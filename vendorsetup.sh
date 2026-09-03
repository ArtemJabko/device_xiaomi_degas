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

# Kernel prebuilts.
# TODO: there is no public degas-kernel repo yet. Two options:
#   1. Build from the Xiaomi OSS kernel source:
#        github.com/android-kernels/xiaomi-bsp-degas-u-oss (branch bsp-degas-u-oss)
#      using the mt6897-devs kernel build stack (kernel_manifest, android_kernel_6.1,
#      android_kernel_device_modules_6.1).
#   2. Create device/xiaomi/degas-kernel with prebuilts extracted from stock
#      boot.img / vendor_boot.img / vendor_dlkm (Image.lz4, dtb/, modules/,
#      kernel-uapi-headers.tar.gz) following the layout of
#      github.com/mt6897-devs/device_xiaomi_duchamp-kernel.
# clone <degas-kernel-repo> device/xiaomi/degas-kernel

# Vendor blobs.
# TODO: generate with device/xiaomi/degas/extract-files.py against a degas
# firmware dump (e.g. OS2.0.202.0.VNEMIXM), then push to a private
# vendor_xiaomi_degas repo and clone it here:
# clone <vendor_xiaomi_degas-repo> vendor/xiaomi/degas

# MediaTek / Xiaomi platform hardware support
clone $MT6897_DEVS/hardware_mediatek.git hardware/mediatek
clone $MT6897_DEVS/hardware_xiaomi.git hardware/xiaomi
clone $MT6897_DEVS/device_mediatek_sepolicy_vndr.git device/mediatek/sepolicy_vndr

# Kernel modules stack (needed when building the kernel from source)
# clone $MT6897_DEVS/android_vendor_mediatek_kernel_modules.git vendor/mediatek/kernel_modules

echo "==> degas dependencies fetched"
