:: This is an example you can edit and use
:: There are numerous parameters you can set, please check Help and Examples folder

@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu randomjuno --pool juno.minerlab.io:3092 --wallet juno-wallet
pause