@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu randompcn --pool pool.pc.am:3333 --wallet pcn-wallet
pause