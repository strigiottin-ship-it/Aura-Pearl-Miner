@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu xhash --pool prlx.coolpool.top:3003 --wallet parallax-wallet --algorithm-gpu qhash --pool qtc.suprnova.cc:5555 --wallet qtc-wallet
pause