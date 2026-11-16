/*
 * SPDX-FileCopyrightText: The LineageOS Project
 * SPDX-License-Identifier: Apache-2.0
 */

package com.xiaomi.settings.display

import android.app.Service
import android.content.Context
import android.content.Intent
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.hardware.display.DisplayManager
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.UserHandle
import android.util.Log
import android.view.Display
import com.xiaomi.settings.touch.TouchFeatureWrapper
import java.io.File

/**
 * Owns the hardware state that only matters while the display is dozing.
 *
 * On stock both of these are driven by MIUI's displayfeature and touchfeature
 * orchestration; on LineageOS nobody owns either, which is why AOD could come
 * up black and why the fingerprint reader went dead a few seconds into AOD.
 *
 * 1. DDIC AOD brightness. The framework contributes nothing here - the backlight
 *    uses a small nonzero transition value (config_screenBrightnessDozeFloat),
 *    while settled AOD luminance is selected through the panel's own
 *    mi_display's doze_brightness node.
 *
 *    The node cannot be trusted as a cache of the DDIC's state: the panel driver
 *    sets its own value inside doze_enable, so a fresh doze entry already reads 1
 *    while the screen is dark, and writing 1 on top of that is dropped ("skip
 *    same doze_brightness set:1") without emitting a DSI command. Force the
 *    change by selecting LBM first. Stay at 5 nit indoors; only request the
 *    60 nit mode in bright surroundings, with hysteresis to avoid oscillation.
 *    A non-wakeup light sensor supplies changes without holding an AP wakelock.
 *
 * 2. UDFPS arming. With Touch_Fod_Enable clear the touch controller does not run
 *    FOD detection at all while dozing - verified on-device, the kernel logs zero
 *    goodix_set_fod_downup events for a finger that is physically on the sensor,
 *    so xiaomi.sensor.fod never fires and SystemUI never gets its AOD interrupt.
 *    UdfpsHandler cannot do this: it only ever sees onFingerDown, which is
 *    downstream of the detection we are trying to enable.
 */
class AodService : Service() {

    private val handler = Handler(Looper.getMainLooper())
    private var wasDozing = false
    private var lastDisplayState = Display.STATE_UNKNOWN
    private var brightAmbient = false
    private var lightSensorRegistered = false
    private var appliedBrightness: Int? = null
    private val sensorManager by lazy { getSystemService(SensorManager::class.java) }
    private val lightSensor by lazy {
        sensorManager.getSensorList(Sensor.TYPE_LIGHT).firstOrNull { !it.isWakeUpSensor }
    }
    private val applyBrightness = Runnable { applyDozeBrightness() }
    private val applyBrightStep = Runnable {
        if (wasDozing && brightAmbient && isDisplayDozing()) {
            write(DOZE_BRIGHTNESS_HBM)
        }
    }

    private val lightListener = object : SensorEventListener {
        override fun onSensorChanged(event: SensorEvent) {
            if (!wasDozing || event.values.isEmpty()) return
            val lux = event.values[0]
            if (!lux.isFinite() || lux < 0) return
            val next = if (brightAmbient) lux > DIM_AMBIENT_LUX else lux >= BRIGHT_AMBIENT_LUX
            if (next == brightAmbient) return
            brightAmbient = next
            handler.removeCallbacks(applyBrightness)
            handler.removeCallbacks(applyBrightStep)
            handler.postDelayed(applyBrightness, AMBIENT_DEBOUNCE_MS)
        }

        override fun onAccuracyChanged(sensor: Sensor, accuracy: Int) {}
    }

    private val displayListener =
        object : DisplayManager.DisplayListener {
            override fun onDisplayAdded(displayId: Int) {}

            override fun onDisplayRemoved(displayId: Int) {}

            override fun onDisplayChanged(displayId: Int) {
                if (displayId != Display.DEFAULT_DISPLAY) return
                updateDisplayState()
            }
        }

    override fun onCreate() {
        super.onCreate()
        if (DEBUG) Log.d(TAG, "onCreate")
        getSystemService(DisplayManager::class.java)
            .registerDisplayListener(displayListener, handler)
        // A restarted service can already be in AOD; no display event is owed.
        updateDisplayState()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        stopLightSensor()
        setFodDetectionEnabled(false)
        getSystemService(DisplayManager::class.java).unregisterDisplayListener(displayListener)
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun getDisplayState(): Int =
        getSystemService(DisplayManager::class.java)
            .getDisplay(Display.DEFAULT_DISPLAY)
            ?.state ?: Display.STATE_UNKNOWN

    private fun isDisplayDozing(): Boolean {
        val state = getDisplayState()
        return state == Display.STATE_DOZE || state == Display.STATE_DOZE_SUSPEND
    }

    private fun updateDisplayState() {
        val state = getDisplayState()
        if (state == lastDisplayState) return
        lastDisplayState = state
        val isDozing = state == Display.STATE_DOZE || state == Display.STATE_DOZE_SUSPEND
        if (DEBUG) Log.d(TAG, "display state=$state dozing=$isDozing")
        handler.removeCallbacks(applyBrightness)
        handler.removeCallbacks(applyBrightStep)
        appliedBrightness = null
        if (isDozing != wasDozing) {
            wasDozing = isDozing
            setFodDetectionEnabled(isDozing)
            if (isDozing) {
                brightAmbient = false
                lightSensor?.let {
                    lightSensorRegistered = sensorManager.registerListener(
                        lightListener, it, LIGHT_SAMPLING_US, handler,
                    )
                }
            } else {
                stopLightSensor()
            }
        }
        if (isDozing) handler.postDelayed(applyBrightness, ENTER_DELAY_MS)
    }

    private fun stopLightSensor() {
        if (!lightSensorRegistered) return
        sensorManager.unregisterListener(lightListener)
        lightSensorRegistered = false
    }

    private fun setFodDetectionEnabled(enabled: Boolean) {
        TouchFeatureWrapper.setModeValue(
            TouchFeatureWrapper.TOUCH_ID_PRIMARY,
            TouchFeatureWrapper.MODE_TOUCH_FOD_ENABLE,
            if (enabled) 1 else 0,
        )
    }

    private fun applyDozeBrightness() {
        if (!wasDozing || !isDisplayDozing()) return
        val target = if (brightAmbient) DOZE_BRIGHTNESS_HBM else DOZE_BRIGHTNESS_LBM
        if (appliedBrightness == target) return
        write(DOZE_BRIGHTNESS_LBM)
        if (target == DOZE_BRIGHTNESS_HBM) {
            handler.postDelayed(applyBrightStep, STEP_DELAY_MS)
        }
    }

    private fun write(value: Int) {
        runCatching { File(DOZE_BRIGHTNESS_NODE).writeText(value.toString()) }
            .onSuccess { appliedBrightness = value }
            .onFailure { e -> Log.e(TAG, "failed to write doze_brightness=$value", e) }
    }

    companion object {
        private const val TAG = "AodService"
        private val DEBUG = Log.isLoggable(TAG, Log.DEBUG)

        private const val DOZE_BRIGHTNESS_NODE =
            "/sys/class/mi_display/disp-DSI-0/doze_brightness"

        /** 0 = normal, 1 = HBM (60 nit), 2 = LBM (5 nit). */
        private const val DOZE_BRIGHTNESS_HBM = 1
        private const val DOZE_BRIGHTNESS_LBM = 2

        private const val ENTER_DELAY_MS = 250L
        private const val STEP_DELAY_MS = 50L
        private const val LIGHT_SAMPLING_US = 1_000_000
        private const val AMBIENT_DEBOUNCE_MS = 1_000L
        private const val BRIGHT_AMBIENT_LUX = 1_500f
        private const val DIM_AMBIENT_LUX = 1_000f

        fun startService(context: Context) {
            context.startServiceAsUser(Intent(context, AodService::class.java), UserHandle.CURRENT)
        }
    }
}
