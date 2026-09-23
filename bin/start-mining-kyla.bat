@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu flex --pool stratum.coinminerz.com:3348 --wallet kcn-wallet
pause