; Independently authored reference source; NASM syntax, 386, flat .COM.
; The standard-library generator encodes this listing without requiring NASM.
bits 16
cpu 386
org 0x100

    push cs
    pop ds
    mov ax, 3
    int 0x10
    mov dx, banner
    mov ah, 9
    int 0x21
    cli
    mov ax, cs
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov eax, 0x13579bdf
    mov ecx, 0x0badf00d
    mov edx, 0x55aa33cc
    mov ebx, 0x2468ace0
    mov esp, 0x0000ff00
    mov ebp, 0x10203040
    mov esi, 0x11223344
    mov edi, 0x55667788
    times 0x160 - ($ - $$ + 0x100) db 0x90
checkpoint:                         ; CS:0160, physical (CS << 4) + 0160
    jmp short checkpoint             ; EB FE, no interrupts or memory writes
    times 0x180 - ($ - $$ + 0x100) db 0
banner:
    db 'DMF CANARY v1', 13, 10
    db 'SOURCE / REGISTERS / RAM', 13, 10
    db 0xda, 0xc4,0xc4,0xc4,0xc4,0xc4,0xc4,0xc4
    db 0xc4,0xc4,0xc4,0xc4,0xc4,0xc4,0xc4, 0xbf, 13,10
    db 0xb3, ' CANARY READY ', 0xb3, 13,10
    db 0xc0, 0xc4,0xc4,0xc4,0xc4,0xc4,0xc4,0xc4
    db 0xc4,0xc4,0xc4,0xc4,0xc4,0xc4,0xc4, 0xd9, 13,10, '$'
    times 0x200 - ($ - $$ + 0x100) db 0
canary_data:                         ; DS:0200; exactly 32 independently known bytes
    db 'DMF-CANARY-v1', 0
    db 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,0xa5,0x5a
