#!/bin/bash
#
# SPDX-License-Identifier: Apache-2.0
#
# Dependency fetcher for Xiaomi 14T (degas) LineageOS 23.2 builds.
# Run from the root of your Android source tree:
#   bash device/xiaomi/degas/vendorsetup.sh

set -e

MT6897_DEVS=https://github.com/mt6897-devs
BRANCH=lineage-23.2

clone() {
    local repo=$1
    local path=$2
    local branch=${3:-$BRANCH}
    if [ -d "$path" ]; then
        echo "==> $path already exists, skipping"
    else
        echo "==> Cloning $repo ($branch) -> $path"
        git clone --depth 1 -b "$branch" "$repo" "$path"
    fi
}

# Device (this tree)
clone https://github.com/ArtemJabko/device_xiaomi_degas.git device/xiaomi/degas

# Kernel prebuilts (prebuilt GKI kernel, modules, dtb, UAPI headers).
clone https://github.com/ArtemJabko/device_xiaomi_degas-kernel.git device/xiaomi/degas-kernel

# Vendor blobs (extracted from stock OS3.0.4.0.WNEMIXM).
clone https://github.com/ArtemJabko/vendor_xiaomi_degas.git vendor/xiaomi/degas

# MediaTek / Xiaomi platform hardware support
clone $MT6897_DEVS/hardware_mediatek.git hardware/mediatek
clone $MT6897_DEVS/hardware_xiaomi.git hardware/xiaomi
clone $MT6897_DEVS/device_mediatek_sepolicy_vndr.git device/mediatek/sepolicy_vndr

# Kernel modules stack (needed when building the kernel from source)
# clone $MT6897_DEVS/android_vendor_mediatek_kernel_modules.git vendor/mediatek/kernel_modules

echo "==> degas dependencies fetched"
