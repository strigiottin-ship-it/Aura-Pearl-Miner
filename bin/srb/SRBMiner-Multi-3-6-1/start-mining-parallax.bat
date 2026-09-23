@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu xhash --pool prlx.coolpool.top:3003 --wallet parallax-wallet
pause