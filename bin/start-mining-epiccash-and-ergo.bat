setx GPU_MAX_HEAP_SIZE 100
setx GPU_MAX_USE_SYNC_OBJECTS 1
setx GPU_SINGLE_ALLOC_PERCENT 100
setx GPU_MAX_ALLOC_PERCENT 100
setx GPU_MAX_SINGLE_ALLOC_PERCENT 100

@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu progpow_epic --algorithm-gpu autolykos2 --pool de.epicmine.io:3333 --pool erg.kryptex.network:7021 --wallet epicmine-username --wallet ergo-wallet --password m=pool --password x
pause