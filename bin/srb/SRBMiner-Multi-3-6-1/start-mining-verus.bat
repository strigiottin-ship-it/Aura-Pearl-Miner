@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu verushash --pool verus.aninterestinghole.xyz:9997 --wallet verus-wallet
pause
