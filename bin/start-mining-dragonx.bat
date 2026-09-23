@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu randomdrgx --pool pool.dragonx.is:3433 --wallet drgx-wallet
pause