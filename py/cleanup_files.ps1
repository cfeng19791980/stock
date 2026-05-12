# 清理其他文件
cd e:\csi10

# 移动测试报告到py文件夹
move test_report.md py\
move test_report_final.md py\
move PROJECT_REVIEW_REPORT.md py\
move package_json.json py\

# 移动bat文件（保留启动.bat）
move run.bat py\
move start.bat py\
move start_v2.bat py\
move start-electron.bat py\
move stop.bat py\
move "停止服务.bat" py\
move "启动JSON版.bat" py\
move "启动系统.bat" py\
move "启动Electron.bat" py\
move "启动Electron.ps1" py\
move Start-Electron.ps1 py\

# 移动其他测试文件
move test.html py\
move test_*.html py\
move test_5001.py py\

Write-Output "清理完成！"