#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

# The stock Xiaomi face service supplies IFace/default.
TARGET_PROVIDES_FACE_UNLOCK_HAL := true

# Evolution X ships GMS by default. Select the GMS A/B branch (erofs + VABC)
# before inheriting device.mk; that is the branch the PixelOS 17 bring-up
# verified booting. Flip to false for a vanilla build.
WITH_GMS := true

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

# Inherit from device makefile.
$(call inherit-product, device/xiaomi/degas/device.mk)

# Evolution X ships its vendor tree at the vendor/lineage path
# (manifest: Evolution-X/vendor_evolution -> vendor/lineage).
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)

# Evolution X specific flags
EVO_BUILD_TYPE := Unofficial
TARGET_ENABLE_BLUR := true
TARGET_SUPPORTS_QUICK_TAP := true
TARGET_BOOT_ANIMATION_RES := 1080

PRODUCT_BRAND := Xiaomi
PRODUCT_DEVICE := degas
PRODUCT_MANUFACTURER := Xiaomi
PRODUCT_MODEL := 2406APNFAG
PRODUCT_NAME := lineage_degas

PRODUCT_CHARACTERISTICS := nosdcard
PRODUCT_GMS_CLIENTID_BASE := android-xiaomi

PRODUCT_BUILD_PROP_OVERRIDES += \
    BuildDesc="missi-user 16 BP2A.250605.031.A3 OS3.0.306.0.WNEEUXM release-keys" \
    DeviceProduct=degas_eea
