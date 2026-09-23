@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu xhash --pool prlx.coolpool.top:3003 --wallet parallax-wallet --algorithm-gpu blake3_decred --pool decred.cedric-crispin.com:4494 --wallet decred-wallet.worker
pause