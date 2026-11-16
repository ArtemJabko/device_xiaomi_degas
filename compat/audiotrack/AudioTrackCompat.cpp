// SPDX-License-Identifier: Apache-2.0
#include <cstddef>
#include <new>
#include <string>

#include <media/AudioTrack.h>

namespace {

// The pinned IMS sink allocates 1496 bytes and reads three inlined getters.
// tools/libsink_compat.py changes those reads to the offsets asserted here.
// Fail the build if a later framework change invalidates this adaptation.
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Winvalid-offsetof"
struct AudioTrackLayoutProbe : android::AudioTrack {
    static constexpr size_t frameCountOffset() {
        return __builtin_offsetof(AudioTrackLayoutProbe, mFrameCount);
    }
    static constexpr size_t frameSizeOffset() {
        return __builtin_offsetof(AudioTrackLayoutProbe, mFrameSize);
    }
    static constexpr size_t statusOffset() {
        return __builtin_offsetof(AudioTrackLayoutProbe, mStatus);
    }
};
static_assert(AudioTrackLayoutProbe::frameCountOffset() == 112);
static_assert(AudioTrackLayoutProbe::frameSizeOffset() == 560);
static_assert(AudioTrackLayoutProbe::statusOffset() == 568);
static_assert(__builtin_offsetof(android::content::AttributionSourceState, pid) == 8);
static_assert(__builtin_offsetof(android::content::AttributionSourceState, uid) == 12);
#pragma clang diagnostic pop
static_assert(sizeof(android::AudioTrack) <= 1496);
static_assert(alignof(android::AudioTrack) <= alignof(std::max_align_t));

}  // namespace

// Export only the missing legacy C1 constructor. Other AudioTrack methods and
// its virtual RefBase lifetime continue to use the current platform library.
extern "C" __attribute__((visibility("default"))) void degas_audio_track_ctor(
        android::AudioTrack* storage, audio_stream_type_t streamType, uint32_t sampleRate,
        audio_format_t format, audio_channel_mask_t channelMask, size_t frameCount,
        audio_output_flags_t flags,
        const android::wp<android::AudioTrack::IAudioTrackCallback>& callback,
        int32_t notificationFrames, audio_session_t sessionId,
        android::AudioTrack::transfer_type transferType, const audio_offload_info_t* offloadInfo,
        const android::content::AttributionSourceState& legacyAttributionSource,
        const audio_attributes_t* attributes, bool doNotReconnect, float maxRequiredSpeed,
        audio_port_handle_t selectedDeviceId)
        __asm__("_ZN7android10AudioTrackC1E19audio_stream_type_tj14audio_format_t"
                "20audio_channel_mask_tm20audio_output_flags_tRKNS_2wpINS0_19IAudioTrackCallbackEEE"
                "i15audio_session_tNS0_13transfer_typeEPK20audio_offload_info_t"
                "RKNS_7content22AttributionSourceStateEPK18audio_attributes_tbfi");

extern "C" void degas_audio_track_ctor(
        android::AudioTrack* storage, audio_stream_type_t streamType, uint32_t sampleRate,
        audio_format_t format, audio_channel_mask_t channelMask, size_t frameCount,
        audio_output_flags_t flags,
        const android::wp<android::AudioTrack::IAudioTrackCallback>& callback,
        int32_t notificationFrames, audio_session_t sessionId,
        android::AudioTrack::transfer_type transferType, const audio_offload_info_t* offloadInfo,
        const android::content::AttributionSourceState& legacyAttributionSource,
        const audio_attributes_t* attributes, bool doNotReconnect, float maxRequiredSpeed,
        audio_port_handle_t selectedDeviceId) {
    // The sole stock call site creates a default attribution object with empty
    // strings, token and chains. Copy its PID/UID only, then use the current
    // parcelable defaults so newly added fields aren't read from old stack memory.
    android::content::AttributionSourceState attributionSource;
    attributionSource.pid = legacyAttributionSource.pid;
    attributionSource.uid = legacyAttributionSource.uid;
    new (storage) android::AudioTrack(streamType, sampleRate, format, channelMask, frameCount,
            flags, callback, notificationFrames, sessionId, transferType, offloadInfo,
            attributionSource, attributes, doNotReconnect, maxRequiredSpeed, selectedDeviceId,
            std::string{});
}
