#!/usr/bin/env python3
"""Patch AnyKernel3 anykernel.sh: flash the GKI signed boot image verbatim.

GKI 1.x (android12 5.10) bootloaders require a full bootimg (ANDROID! v4
header + kernel + GKI first-stage ramdisk + AVB footer). Repacking a bare
Image makes the device bootloop. When a signed image is present in the AK3
root, dd it to the boot partition as-is. Otherwise fall back to the
original split_boot / flash_boot path (bare kernel / modules-only mode).
"""
import sys

OLD = """# boot install
split_boot

if [ -f "$SPLITIMG/ramdisk.cpio" ]; then
    unpack_ramdisk
    write_boot
else
    flash_boot
fi
"""

NEW = """# boot install
if [ -f "$AKHOME/boot-signed.img" ]; then
    # GKI signed boot image: ANDROID! v4 header + kernel + GKI first-stage
    # ramdisk + AVB testkey footer. Flash it verbatim so the GKI 1.x ABL
    # gets a bootable bootimg (a bare Image alone causes a bootloop).
    ui_print "  -> GKI signed boot image: flashing verbatim to $BLOCK"
    blockdev --setrw $BLOCK 2>/dev/null
    if [ -f "$BIN/flash_erase" -a -f "$BIN/nandwrite" ]; then
        flash_erase $BLOCK 0 0
        nandwrite -p $BLOCK $AKHOME/boot-signed.img
    elif [ "$CUSTOMDD" ]; then
        dd if=/dev/zero of=$BLOCK $CUSTOMDD 2>/dev/null
        dd if=$AKHOME/boot-signed.img of=$BLOCK $CUSTOMDD
    else
        cat $AKHOME/boot-signed.img /dev/zero > $BLOCK 2>/dev/null || true
    fi
    [ $? -eq 0 ] || abort "Flashing GKI signed boot image failed. Aborting..."
else
    split_boot
    if [ -f "$SPLITIMG/ramdisk.cpio" ]; then
        unpack_ramdisk
        write_boot
    else
        flash_boot
    fi
fi
"""


def main() -> None:
    path = sys.argv[1]
    s = open(path).read()
    if "boot-signed.img" in s:
        print("anykernel.sh already carries the GKI signed-flash path; skipping")
        return
    if OLD not in s:
        sys.exit(f"ERROR: '# boot install' block not found in {path}")
    open(path, "w").write(s.replace(OLD, NEW, 1))
    print("anykernel.sh: GKI signed boot image flash path installed")


if __name__ == "__main__":
    main()
