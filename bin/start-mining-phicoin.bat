@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu phihash --pool eu.neuropool.net:10110 --wallet phicoin-wallet
pause