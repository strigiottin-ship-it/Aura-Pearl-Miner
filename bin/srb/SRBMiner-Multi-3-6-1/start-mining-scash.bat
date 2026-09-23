@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu randomscash --pool stratum-eu.rplant.xyz:7019 --wallet scash-wallet
pause