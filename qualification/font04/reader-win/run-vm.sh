#!/bin/bash
# Windows 11 eval VM for the FONT-04 Adobe Reader check. Headless; control via QMP + SMB share.
set -e
V=$(cd "$(dirname "$0")" && pwd)
cd "$V"
[ -f disk.qcow2 ] || qemu-img create -f qcow2 disk.qcow2 80G
[ -f OVMF_VARS.fd ] || cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd OVMF_VARS.fd
T="$HOME/.local/share/scanweave-winvm/tpm"; mkdir -p "$T"
swtpm socket --tpmstate dir="$T" --ctrl type=unixio,path="$T/swtpm.sock" --tpm2 --daemon --pid file="$T/swtpm.pid" --log file="$T/swtpm.log"
CD=()
[ "${INSTALL:-0}" = 1 ] && CD=(-drive file=win11-eval.iso,media=cdrom,if=none,id=cd0 -device ide-cd,drive=cd0,bus=ide.0,bootindex=0)
exec qemu-system-x86_64 \
  -name swreader -machine q35,accel=kvm,smm=on -cpu host -smp 8 -m 12G \
  -global driver=cfi.pflash01,property=secure,value=on \
  -drive if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.ms.fd \
  -drive if=pflash,format=raw,unit=1,file=OVMF_VARS.fd \
  -chardev socket,id=chrtpm,path="$T/swtpm.sock" -tpmdev emulator,id=tpm0,chardev=chrtpm -device tpm-tis,tpmdev=tpm0 \
  -drive file=disk.qcow2,if=none,id=hd0,cache=unsafe,discard=unmap -device ahci,id=ahci -device ide-hd,drive=hd0,bus=ahci.0,bootindex=1 \
  "${CD[@]}" \
  -drive file=cfg.iso,media=cdrom,if=none,id=cd1 -device ide-cd,drive=cd1,bus=ide.1 \
  -nic user,model=e1000e,smb="$V/share" \
  -device qemu-xhci -device usb-tablet \
  -vga none -device VGA,edid=on,xres=1920,yres=1440 -display none -vnc 127.0.0.1:17 \
  -qmp unix:"$V/qmp.sock",server=on,wait=off \
  -rtc base=utc
