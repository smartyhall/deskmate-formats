/* MDIAG - resident guest mouse telemetry for graphical input qualification.
 *
 * Original code for this project (GPL-3.0-or-later OR CC-BY-SA-4.0).
 *
 * Installs an INT 1Ch (timer tick) handler that samples INT 33h function 3 and
 * publishes the driver's cursor position, button state and button transition
 * counters in a fixed record. The record is located by its signature, so the
 * guest segment does not have to be fixed; the install line prints the segment
 * for convenience.
 *
 *   offset  size  field
 *   0       8     signature "MDIAG001"
 *   8       2     x            INT 33h CX
 *   10      2     y            INT 33h DX
 *   12      2     buttons      INT 33h BX (bit 0 left, 1 right, 2 middle)
 *   14      2     presses      button transitions 0 -> 1
 *   16      2     releases     button transitions 1 -> 0
 *   18      2     ticks        timer ticks sampled
 *   20      2     version      1
 *   22      2     reserved     0
 *
 * The handler chains to the previous INT 1Ch vector. It never changes mouse
 * state, never writes outside its own segment, and displays nothing after
 * installation.
 *
 * Build: build.py assembles with GNU as (.code16, .org 0x100) and strips the
 * 0x100-byte origin gap from the flat image.
 */
	.code16
	.text
	.org	0x100
	.globl	_start

	/* The published record lives in its own block inside the resident area. */
	.set	REC_X, record+8
	.set	REC_Y, record+10
	.set	REC_BUTTONS, record+12
	.set	REC_PRESSES, record+14
	.set	REC_RELEASES, record+16
	.set	REC_TICKS, record+18
	.set	REC_VERSION, record+20
	.set	REC_RESERVED, record+22

_start:
	push	%cs
	pop	%ds
	push	%cs
	pop	%es

	/* Require an installed driver: INT 33h function 0 returns FFFFh in AX. */
	xor	%ax, %ax
	int	$0x33
	cmp	$0xffff, %ax
	jne	no_driver

	mov	$signature_text, %si
	mov	$record, %di
	mov	$8, %cx
	cld
	rep	movsb
	movw	$1, REC_VERSION
	movw	$0, REC_RESERVED
	movw	$0, REC_X
	movw	$0, REC_Y
	movw	$0, REC_BUTTONS
	movw	$0, REC_PRESSES
	movw	$0, REC_RELEASES
	movw	$0, REC_TICKS
	movw	$0, previous_buttons

	/* Save and replace INT 1Ch. */
	mov	$0x351c, %ax
	int	$0x21
	mov	%bx, old_1c
	mov	%es, old_1c+2
	mov	$0x251c, %ax
	mov	$mdiag_tick, %dx
	int	$0x21

	mov	$message, %dx
	mov	$0x09, %ah
	int	$0x21
	mov	%cs, %bx
	mov	$4, %cx
print_segment:
	rol	$4, %bx
	mov	%bx, %dx
	and	$0x000f, %dx
	cmp	$10, %dl
	jb	digit
	add	$('A' - 10 - '0'), %dl
digit:
	add	$'0', %dl
	mov	$0x02, %ah
	int	$0x21
	loop	print_segment
	mov	$suffix, %dx
	mov	$0x09, %ah
	int	$0x21

	/* Keep the PSP (0x100 bytes) and the resident program; AH=31h. */
	mov	$program_end, %dx
	add	$0x010f, %dx
	shr	$4, %dx
	mov	$0x31, %ah
	int	$0x21

no_driver:
	mov	$missing, %dx
	mov	$0x09, %ah
	int	$0x21
	mov	$0x4c01, %ax
	int	$0x21

/* INT 1Ch handler: sample INT 33h, count transitions, chain. */
mdiag_tick:
	push	%ax
	push	%bx
	push	%cx
	push	%dx
	push	%si
	push	%ds
	mov	%cs, %ax
	mov	%ax, %ds

	mov	$3, %ax
	int	$0x33
	mov	%cx, REC_X
	mov	%dx, REC_Y
	mov	%bx, REC_BUTTONS

	/* changed = previous XOR current; presses = changed AND current. */
	mov	previous_buttons, %ax
	xor	%bx, %ax
	mov	%ax, %si
	and	%bx, %si
	test	$1, %si
	jz	1f
	incw	REC_PRESSES
1:	test	$2, %si
	jz	2f
	incw	REC_PRESSES
2:	test	$4, %si
	jz	3f
	incw	REC_PRESSES
3:
	/* releases = changed AND NOT current */
	mov	previous_buttons, %ax
	xor	%bx, %ax
	not	%bx
	and	%bx, %ax
	mov	%ax, %si
	test	$1, %si
	jz	4f
	incw	REC_RELEASES
4:	test	$2, %si
	jz	5f
	incw	REC_RELEASES
5:	test	$4, %si
	jz	6f
	incw	REC_RELEASES
6:
	mov	REC_BUTTONS, %bx
	mov	%bx, previous_buttons
	incw	REC_TICKS

	pop	%ds
	pop	%si
	pop	%dx
	pop	%cx
	pop	%bx
	pop	%ax
	ljmp	*%cs:old_1c

signature_text:
	.ascii	"MDIAG001"
message:
	.ascii	"MDIAG 1.00 resident, segment "
suffix:
	.ascii	"\r\n$"
missing:
	.ascii	"MDIAG: no mouse driver installed (INT 33h absent)$"
	.p2align 1
old_1c:
	.long	0
previous_buttons:
	.word	0
	.p2align 1
record:
	.space	24, 0
program_end:
