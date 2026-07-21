/* Wine spec PE header - necessary for Wine to load this .so as a builtin DLL */
/* Generated manually following Wine's winebuild output_module() pattern */

.text
.globl __wine_spec_nt_header
.type __wine_spec_nt_header, @object

__wine_spec_nt_header:
    /* DOS header (IMAGE_DOS_HEADER) */
    .byte 0x4d, 0x5a                          /* e_magic = "MZ" */
    .space 58                                 /* e_lfanew at offset 60 */
    .long 0x80                                /* e_lfanew = 0x80 */

    /* PE signature "PE\0\0" */
    .byte 0x50, 0x45, 0x00, 0x00

    /* IMAGE_FILE_HEADER */
    .short 0x8664                             /* Machine = AMD64 */
    .short 0                                  /* NumberOfSections = 0 (for builtin) */
    .long 0                                   /* TimeDateStamp */
    .long 0                                   /* PointerToSymbolTable */
    .long 0                                   /* NumberOfSymbols */
    .short 0                                  /* SizeOfOptionalHeader */
    .short 0x2002                             /* Characteristics = IMAGE_FILE_DLL | IMAGE_FILE_EXECUTABLE_IMAGE */

    /* IMAGE_OPTIONAL_HEADER (minimal, just the Magic) */
    .short 0x020b                             /* Magic = PE32+ (0x020b) */

    /* Padding to make a reasonable image */
    .space 200

.size __wine_spec_nt_header, . - __wine_spec_nt_header
