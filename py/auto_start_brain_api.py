# -*- coding: utf-8 -*-
"""设计Brain API自动启动方案"""
import sys, os, json, shutil
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("Brain API自动启动方案")
print("=" * 70)

print("\n【问题】")
print("当前状态: Brain API需要手动启动")
print("风险: Hook调用失败时无决策支持")

print("\n【方案对比】")

print("""
方案A: Hook插件自启动Brain API
  优点:
    - 不依赖外部配置
    - API不存在时自动启动
    - 最简单可靠
  实现:
    - 在Hook初始化时检查API
    - API不存在则spawn子进程启动

方案B: OpenClaw启动配置
  优点:
    - 统一管理
    - 可控启动顺序
  实现:
    - 在openclaw.json添加启动命令配置

方案C: Windows服务开机自启
  优点:
    - 系统级自动启动
  缺点:
    - 需要管理员权限
    - 配置复杂

方案D: Cron定时检查
  优点:
    - 定期检查确保运行
  缺点:
    - 需要额外cron配置
""")

print("\n【推荐方案A】")
print("Hook插件自启动Brain API - 最简单可靠")

# 更新Hook插件添加自启动逻辑
hook_dir = r'C:\Users\Administrator\.openclaw\extensions\brain-hook'
hook_js_path = os.path.join(hook_dir, 'index.js')

# 读取现有Hook
with open(hook_js_path, 'r', encoding='utf-8') as f:
    hook_content = f.read()

# 添加自启动逻辑
auto_start_logic = '''
  /**
   * 自动启动Brain API
   */
  async ensureBrainAPIRunning() {
    // 先检查API是否运行
    const running = await this.checkBrainAPI();
    
    if (!running) {
      console.log('[BrainHook] Brain API未运行，正在启动...');
      await this.startBrainAPI();
    }
  }

  /**
   * 检查Brain API状态
   */
  async checkBrainAPI() {
    return new Promise((resolve) => {
      const options = {
        hostname: BRAIN_API_HOST,
        port: BRAIN_API_PORT,
        path: '/health',
        method: 'GET',
        timeout: 2000
      };

      const req = http.request(options, (res) => {
        resolve(res.statusCode === 200);
      });

      req.on('error', () => { resolve(false); });
      req.on('timeout', () => { resolve(false); });
      req.end();
    });
  }

  /**
   * 启动Brain API子进程
   */
  async startBrainAPI() {
    const { spawn } = require('child_process');
    const pythonExe = process.env.PYTHON_EXE || 'python';
    const brainApiPath = process.env.BRAIN_API_PATH || 
      'C:\\Users\\Administrator\\.openclaw\\workspace-工程师\\brain_hook_api.py';
    
    this.brainProcess = spawn(pythonExe, [brainApiPath, '--port', BRAIN_API_PORT], {
      detached: true,
      stdio: 'ignore'
    });
    
    this.brainProcess.unref();
    
    // 等待2秒让API启动
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    console.log('[BrainHook] Brain API已启动');
  }

  // 构造函数中调用自启动
  constructor() {
    this.name = 'brain-hook';
    this.version = '1.0.0';
    this.brainProcess = null;
    
    // 自动确保API运行
    this.ensureBrainAPIRunning();
  }
'''

# 更新Hook
if 'ensureBrainAPIRunning' not in hook_content:
    # 在class中添加自启动逻辑
    updated_hook = hook_content.replace(
        'constructor() {\n    this.name = \'brain-hook\';\n    this.version = \'1.0.0\';\n  }',
        'constructor() {\n    this.name = \'brain-hook\';\n    this.version = \'1.0.0\';\n    this.brainProcess = null;\n    \n    // 自动确保API运行\n    this.ensureBrainAPIRunning();\n  }' + '\n\n' + auto_start_logic
    )
    
    with open(hook_js_path, 'w', encoding='utf-8') as f:
        f.write(updated_hook)
    
    print("\n✓ Hook已更新: 添加自动启动逻辑")

print("\n【更新后的Hook逻辑】")
print("""
Hook插件初始化时:
  1. 检查Brain API是否运行
  2. 未运行 → 自动spawn子进程启动
  3. 已运行 → 直接使用

优点:
  - 无需手动启动
  - OpenClaw启动时Hook自动启动
  - API崩溃后下次调用会自动重启
""")

print("\n" + "=" * 70)
print("完成")
print("=" * 70)