/* File generated automatically from nvcuda.spec; do not edit! */
/* This file can be copied, modified and distributed without restriction. */


	.section ".init","ax"
	jmp 1f
__wine_spec_pe_header:
	.skip 69632
1:

	.data
	.balign 8
	.globl __wine_spec_nt_header
__wine_spec_nt_header:
.L__wine_spec_rva_base:
	.long 0x4550
	.short 0x8664
	.short 0
	.long 1057516690
	.long 0
	.long 0
	.short 240
	.short 0x2022
	.short 0x020b
	.byte 7
	.byte 10
	.long 0
	.long 0
	.long 0
	.globl DllMain
	.quad __wine_spec_dll_entry
	.quad __wine_spec_pe_header
	.long 4096
	.long 4096
	.short 1,0
	.short 0,0
	.short 4,0
	.long 0
	.long _end - .L__wine_spec_rva_base
	.long 4096
	.long 0
	.short 0x0003
	.short 0x0160
	.quad 1048576,4096
	.quad 1048576,4096
	.long 0
	.long 16
	.long .L__wine_spec_exports - .L__wine_spec_rva_base
	.long .L__wine_spec_exports_end - .L__wine_spec_exports
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0
	.long 0,0

/* export table */

	.section .data
	.balign 4
.L__wine_spec_exports:
	.long 0
	.long 1057516690
	.long 0
	.long .L__wine_spec_exp_names - .L__wine_spec_rva_base
	.long 1
	.long 71
	.long 71
	.long .L__wine_spec_exports_funcs  - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_name_ptrs - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_ordinals - .L__wine_spec_rva_base

.L__wine_spec_exports_funcs:
	.quad cuInit
	.quad cuDriverGetVersion
	.quad cuDeviceGet
	.quad cuDeviceGetCount
	.quad cuDeviceGetName
	.quad cuDeviceGetUuid
	.quad cuDeviceGetAttribute
	.quad cuDevicePrimaryCtxRetain
	.quad cuDevicePrimaryCtxRelease
	.quad cuDevicePrimaryCtxReset
	.quad cuCtxCreate
	.quad cuCtxDestroy
	.quad cuCtxGetCurrent
	.quad cuCtxSetCurrent
	.quad cuCtxGetDevice
	.quad cuCtxSynchronize
	.quad cuCtxPushCurrent
	.quad cuCtxPopCurrent
	.quad cuMemAlloc
	.quad cuMemAllocHost
	.quad cuMemFree
	.quad cuMemFreeHost
	.quad cuMemcpyHtoD
	.quad cuMemcpyDtoH
	.quad cuMemcpyHtoDAsync
	.quad cuMemcpyDtoHAsync
	.quad cuMemsetD8
	.quad cuMemsetD32
	.quad cuArrayCreate
	.quad cuArrayDestroy
	.quad cuArrayGetDescriptor
	.quad cuModuleLoadData
	.quad cuModuleLoadDataEx
	.quad cuModuleGetFunction
	.quad cuModuleGetGlobal
	.quad cuModuleUnload
	.quad cuLaunchKernel
	.quad cuLaunchCooperativeKernel
	.quad cuStreamCreate
	.quad cuStreamDestroy
	.quad cuStreamSynchronize
	.quad cuStreamWaitEvent
	.quad cuEventCreate
	.quad cuEventDestroy
	.quad cuEventRecord
	.quad cuEventSynchronize
	.quad cuEventElapsedTime
	.quad cuGetErrorString
	.quad cuGetErrorName
	.quad cuFuncSetAttribute
	.quad cuFuncSetCacheConfig
	.quad cuFuncSetSharedMemConfig
	.quad cuOccupancyMaxPotentialBlockSize
	.quad cuOccupancyMaxActiveBlocksPerMultiprocessor
	.quad cuPointerGetAttribute
	.quad cuPointerSetAttribute
	.quad cuPointerGetAttributes
	.quad cuCtxGetApiVersion
	.quad cuCtxGetCacheConfig
	.quad cuCtxSetCacheConfig
	.quad cuCtxGetSharedMemConfig
	.quad cuCtxSetSharedMemConfig
	.quad cuCtxEnablePeerAccess
	.quad cuCtxDisablePeerAccess
	.quad cuCtxCanAccessPeer
	.quad cuDeviceCanAccessPeer
	.quad cuDeviceGetP2PAttribute
	.quad cuGetProcAddress
	.quad cuProfilerStart
	.quad cuProfilerStop
	.quad cuProfilerInitialize

.L__wine_spec_exp_name_ptrs:
	.long .L__wine_spec_exp_names + 11 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 25 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 40 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 61 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 80 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 92 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 105 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 128 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 150 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 169 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 189 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 205 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 220 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 244 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 260 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 277 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 297 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 313 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 337 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 354 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 376 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 388 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 409 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 426 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 442 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 466 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 482 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 508 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 532 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 557 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 576 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 590 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 605 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 624 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 638 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 657 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 676 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 697 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 722 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 737 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 754 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 771 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 778 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 804 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 819 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 830 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 845 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 855 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 869 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 882 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 900 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 913 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 931 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 943 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 954 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 974 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 992 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1009 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1028 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1043 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1087 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1120 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1142 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1165 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1187 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1208 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1224 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1239 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1254 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1270 - .L__wine_spec_rva_base
	.long .L__wine_spec_exp_names + 1290 - .L__wine_spec_rva_base

.L__wine_spec_exp_ordinals:
	.short 28
	.short 29
	.short 30
	.short 64
	.short 10
	.short 11
	.short 63
	.short 62
	.short 57
	.short 58
	.short 12
	.short 14
	.short 60
	.short 17
	.short 16
	.short 59
	.short 13
	.short 61
	.short 15
	.short 65
	.short 2
	.short 6
	.short 3
	.short 4
	.short 66
	.short 5
	.short 8
	.short 9
	.short 7
	.short 1
	.short 42
	.short 43
	.short 46
	.short 44
	.short 45
	.short 49
	.short 50
	.short 51
	.short 48
	.short 47
	.short 67
	.short 0
	.short 37
	.short 36
	.short 18
	.short 19
	.short 20
	.short 21
	.short 23
	.short 25
	.short 22
	.short 24
	.short 27
	.short 26
	.short 33
	.short 34
	.short 31
	.short 32
	.short 35
	.short 53
	.short 52
	.short 54
	.short 56
	.short 55
	.short 70
	.short 68
	.short 69
	.short 38
	.short 39
	.short 40
	.short 41
	.short 0
	.long 0xdeb90002
	.long 0

.L__wine_spec_exp_names:
	.string "nvcuda.dll"
	.string "cuArrayCreate"
	.string "cuArrayDestroy"
	.string "cuArrayGetDescriptor"
	.string "cuCtxCanAccessPeer"
	.string "cuCtxCreate"
	.string "cuCtxDestroy"
	.string "cuCtxDisablePeerAccess"
	.string "cuCtxEnablePeerAccess"
	.string "cuCtxGetApiVersion"
	.string "cuCtxGetCacheConfig"
	.string "cuCtxGetCurrent"
	.string "cuCtxGetDevice"
	.string "cuCtxGetSharedMemConfig"
	.string "cuCtxPopCurrent"
	.string "cuCtxPushCurrent"
	.string "cuCtxSetCacheConfig"
	.string "cuCtxSetCurrent"
	.string "cuCtxSetSharedMemConfig"
	.string "cuCtxSynchronize"
	.string "cuDeviceCanAccessPeer"
	.string "cuDeviceGet"
	.string "cuDeviceGetAttribute"
	.string "cuDeviceGetCount"
	.string "cuDeviceGetName"
	.string "cuDeviceGetP2PAttribute"
	.string "cuDeviceGetUuid"
	.string "cuDevicePrimaryCtxRelease"
	.string "cuDevicePrimaryCtxReset"
	.string "cuDevicePrimaryCtxRetain"
	.string "cuDriverGetVersion"
	.string "cuEventCreate"
	.string "cuEventDestroy"
	.string "cuEventElapsedTime"
	.string "cuEventRecord"
	.string "cuEventSynchronize"
	.string "cuFuncSetAttribute"
	.string "cuFuncSetCacheConfig"
	.string "cuFuncSetSharedMemConfig"
	.string "cuGetErrorName"
	.string "cuGetErrorString"
	.string "cuGetProcAddress"
	.string "cuInit"
	.string "cuLaunchCooperativeKernel"
	.string "cuLaunchKernel"
	.string "cuMemAlloc"
	.string "cuMemAllocHost"
	.string "cuMemFree"
	.string "cuMemFreeHost"
	.string "cuMemcpyDtoH"
	.string "cuMemcpyDtoHAsync"
	.string "cuMemcpyHtoD"
	.string "cuMemcpyHtoDAsync"
	.string "cuMemsetD32"
	.string "cuMemsetD8"
	.string "cuModuleGetFunction"
	.string "cuModuleGetGlobal"
	.string "cuModuleLoadData"
	.string "cuModuleLoadDataEx"
	.string "cuModuleUnload"
	.string "cuOccupancyMaxActiveBlocksPerMultiprocessor"
	.string "cuOccupancyMaxPotentialBlockSize"
	.string "cuPointerGetAttribute"
	.string "cuPointerGetAttributes"
	.string "cuPointerSetAttribute"
	.string "cuProfilerInitialize"
	.string "cuProfilerStart"
	.string "cuProfilerStop"
	.string "cuStreamCreate"
	.string "cuStreamDestroy"
	.string "cuStreamSynchronize"
	.string "cuStreamWaitEvent"
	.balign 8
.L__wine_spec_exports_end:
.L__wine_spec_relay_descr:
	.quad 0xdeb90002
	.quad 0
	.quad 0
	.quad __wine_spec_relay_entry_points
	.quad .L__wine_spec_relay_entry_point_offsets
	.quad .L__wine_spec_relay_args_string
	.section .rodata
	.balign 4
.L__wine_spec_relay_entry_point_offsets:
	.long __wine_spec_relay_entry_point_1-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_2-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_3-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_4-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_5-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_6-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_7-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_8-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_9-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_10-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_11-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_12-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_13-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_14-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_15-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_16-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_17-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_18-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_19-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_20-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_21-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_22-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_23-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_24-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_25-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_26-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_27-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_28-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_29-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_30-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_31-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_32-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_33-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_34-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_35-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_36-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_37-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_38-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_39-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_40-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_41-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_42-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_43-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_44-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_45-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_46-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_47-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_48-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_49-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_50-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_51-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_52-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_53-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_54-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_55-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_56-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_57-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_58-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_59-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_60-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_61-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_62-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_63-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_64-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_65-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_66-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_67-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_68-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_69-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_70-__wine_spec_relay_entry_points
	.long __wine_spec_relay_entry_point_71-__wine_spec_relay_entry_points
.L__wine_spec_relay_args_string:
	.string "iI"
	.text
__wine_spec_relay_entry_points:
	nop
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_1:
	movq %rcx,8(%rsp)
	movl $0,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_2:
	movq %rcx,8(%rsp)
	movl $1,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_3:
	movq %rcx,8(%rsp)
	movl $2,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_4:
	movq %rcx,8(%rsp)
	movl $3,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_5:
	movq %rcx,8(%rsp)
	movl $4,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_6:
	movq %rcx,8(%rsp)
	movl $5,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_7:
	movq %rcx,8(%rsp)
	movl $6,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_8:
	movq %rcx,8(%rsp)
	movl $7,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_9:
	movq %rcx,8(%rsp)
	movl $8,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_10:
	movq %rcx,8(%rsp)
	movl $9,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_11:
	movq %rcx,8(%rsp)
	movl $10,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_12:
	movq %rcx,8(%rsp)
	movl $11,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_13:
	movq %rcx,8(%rsp)
	movl $12,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_14:
	movq %rcx,8(%rsp)
	movl $13,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_15:
	movq %rcx,8(%rsp)
	movl $14,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_16:
	movq %rcx,8(%rsp)
	movl $15,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_17:
	movq %rcx,8(%rsp)
	movl $16,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_18:
	movq %rcx,8(%rsp)
	movl $17,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_19:
	movq %rcx,8(%rsp)
	movl $18,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_20:
	movq %rcx,8(%rsp)
	movl $19,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_21:
	movq %rcx,8(%rsp)
	movl $20,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_22:
	movq %rcx,8(%rsp)
	movl $21,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_23:
	movq %rcx,8(%rsp)
	movl $22,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_24:
	movq %rcx,8(%rsp)
	movl $23,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_25:
	movq %rcx,8(%rsp)
	movl $24,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_26:
	movq %rcx,8(%rsp)
	movl $25,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_27:
	movq %rcx,8(%rsp)
	movl $26,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_28:
	movq %rcx,8(%rsp)
	movl $27,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_29:
	movq %rcx,8(%rsp)
	movl $28,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_30:
	movq %rcx,8(%rsp)
	movl $29,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_31:
	movq %rcx,8(%rsp)
	movl $30,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_32:
	movq %rcx,8(%rsp)
	movl $31,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_33:
	movq %rcx,8(%rsp)
	movl $32,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_34:
	movq %rcx,8(%rsp)
	movl $33,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_35:
	movq %rcx,8(%rsp)
	movl $34,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_36:
	movq %rcx,8(%rsp)
	movl $35,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_37:
	movq %rcx,8(%rsp)
	movl $36,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_38:
	movq %rcx,8(%rsp)
	movl $37,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_39:
	movq %rcx,8(%rsp)
	movl $38,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_40:
	movq %rcx,8(%rsp)
	movl $39,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_41:
	movq %rcx,8(%rsp)
	movl $40,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_42:
	movq %rcx,8(%rsp)
	movl $41,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_43:
	movq %rcx,8(%rsp)
	movl $42,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_44:
	movq %rcx,8(%rsp)
	movl $43,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_45:
	movq %rcx,8(%rsp)
	movl $44,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_46:
	movq %rcx,8(%rsp)
	movl $45,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_47:
	movq %rcx,8(%rsp)
	movl $46,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_48:
	movq %rcx,8(%rsp)
	movl $47,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_49:
	movq %rcx,8(%rsp)
	movl $48,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_50:
	movq %rcx,8(%rsp)
	movl $49,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_51:
	movq %rcx,8(%rsp)
	movl $50,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_52:
	movq %rcx,8(%rsp)
	movl $51,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_53:
	movq %rcx,8(%rsp)
	movl $52,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_54:
	movq %rcx,8(%rsp)
	movl $53,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_55:
	movq %rcx,8(%rsp)
	movl $54,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_56:
	movq %rcx,8(%rsp)
	movl $55,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_57:
	movq %rcx,8(%rsp)
	movl $56,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_58:
	movq %rcx,8(%rsp)
	movl $57,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_59:
	movq %rcx,8(%rsp)
	movl $58,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_60:
	movq %rcx,8(%rsp)
	movl $59,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_61:
	movq %rcx,8(%rsp)
	movl $60,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_62:
	movq %rcx,8(%rsp)
	movl $61,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_63:
	movq %rcx,8(%rsp)
	movl $62,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_64:
	movq %rcx,8(%rsp)
	movl $63,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_65:
	movq %rcx,8(%rsp)
	movl $64,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_66:
	movq %rcx,8(%rsp)
	movl $65,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_67:
	movq %rcx,8(%rsp)
	movl $66,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_68:
	movq %rcx,8(%rsp)
	movl $67,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_69:
	movq %rcx,8(%rsp)
	movl $68,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_70:
	movq %rcx,8(%rsp)
	movl $69,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.balign 4
	.long 0x90909090,0x90909090
__wine_spec_relay_entry_point_71:
	movq %rcx,8(%rsp)
	movl $70,%edx
	leaq .L__wine_spec_relay_descr(%rip),%rcx
	callq *8(%rcx)
	ret
	.section .note.GNU-stack,"",@progbits
