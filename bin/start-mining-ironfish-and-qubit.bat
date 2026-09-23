setx GPU_MAX_HEAP_SIZE 100
setx GPU_MAX_USE_SYNC_OBJECTS 1
setx GPU_SINGLE_ALLOC_PERCENT 100
setx GPU_MAX_ALLOC_PERCENT 100
setx GPU_MAX_SINGLE_ALLOC_PERCENT 100

@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu fishhash --pool iron.kryptex.network:7017 --wallet ironfish-wallet.worker --algorithm-gpu qhash --pool qtc.suprnova.cc:5555 --wallet qtc-wallet
pause