:: This is an example you can edit and use
:: There are numerous parameters you can set, please check Help and Examples folder

@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu randomc64 --pool c64.suprnova.cc:6465 --wallet c64-wallet
pause