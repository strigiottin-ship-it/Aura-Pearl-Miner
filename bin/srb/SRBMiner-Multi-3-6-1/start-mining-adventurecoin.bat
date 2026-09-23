@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu yespoweradvc --pool stratum-eu.rplant.xyz:7149 --wallet advc-wallet
pause
