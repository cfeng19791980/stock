# -*- coding: utf-8 -*-
"""创建Brain Hook插件"""
import sys, os, json, shutil
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("Brain Hook插件实现")
print("=" * 70)

base_dir = r'C:\Users\Administrator\.openclaw\extensions'
hook_dir = os.path.join(base_dir, 'brain-hook')

# 创建目录
if not os.path.exists(hook_dir):
    os.makedirs(hook_dir)
    print(f"\n✓ 创建目录: {hook_dir}")

print("\n【方案设计】")

print("""
Hook插件架构:

  用户请求 → OpenClaw接收 → Brain Hook拦截 → Brain决策 → 执行 → 反馈

实现方式:
  1. 创建brain-hook插件
  2. 监听agent.request事件
  3. 调用Brain API决策
  4. 返回决策结果或执行指令
""")

# 创建插件主文件
hook_js = '''/**
 * Brain Hook Plugin - 强制Brain决策流程
 * 在每个用户请求前拦截，调用Brain系统决策
 */

const http = require('http');

const BRAIN_API_PORT = 5000;
const BRAIN_API_HOST = 'localhost';

class BrainHook {
  constructor() {
    this.name = 'brain-hook';
    this.version = '1.0.0';
  }

  /**
   * Hook入口 - 在请求处理前调用
   */
  async preProcess(context) {
    const { userInput, agentId, sessionId } = context;
    
    // 调用Brain API决策
    const decision = await this.callBrainAPI(userInput);
    
    // 根据置信度决定行动
    if (decision.confidence < 0.5) {
      // 低置信度：注入请示提示
      return {
        action: 'ask_user',
        reason: decision.reason,
        confidence: decision.confidence
      };
    }
    
    // 高置信度：记录决策，允许执行
    this.logDecision(decision);
    
    return {
      action: 'proceed',
      decision: decision
    };
  }

  /**
   * 调用Brain API
   */
  async callBrainAPI(query) {
    return new Promise((resolve, reject) => {
      const postData = JSON.stringify({ query });
      
      const options = {
        hostname: BRAIN_API_HOST,
        port: BRAIN_API_PORT,
        path: '/decide',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(postData)
        }
      };

      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            resolve({ confidence: 0.3, reason: 'Brain API error' });
          }
        });
      });

      req.on('error', (e) => {
        resolve({ confidence: 0.3, reason: 'Brain API unavailable' });
      });

      req.write(postData);
      req.end();
    });
  }

  /**
   * 记录决策
   */
  logDecision(decision) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      decision_id: decision.decision_id,
      confidence: decision.confidence,
      action: decision.action
    };
    
    // 写入决策日志
    console.log('[BrainHook]', JSON.stringify(logEntry));
  }

  /**
   * Hook出口 - 在请求处理后调用（反馈）
   */
  async postProcess(context, result) {
    const { userInput } = context;
    const { success, output, error } = result;
    
    // 调用Brain API记录反馈
    await this.recordFeedback(userInput, success, output);
    
    return result;
  }

  /**
   * 记录反馈
   */
  async recordFeedback(query, success, output) {
    return new Promise((resolve) => {
      const postData = JSON.stringify({
        query,
        success,
        output: output?.substring(0, 500)
      });
      
      const options = {
        hostname: BRAIN_API_HOST,
        port: BRAIN_API_PORT,
        path: '/feedback',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(postData)
        }
      };

      const req = http.request(options, (res) => {
        resolve();
      });

      req.on('error', () => { resolve(); });
      req.write(postData);
      req.end();
    });
  }
}

// 导出Hook
module.exports = new BrainHook();
'''

hook_js_path = os.path.join(hook_dir, 'index.js')
with open(hook_js_path, 'w', encoding='utf-8') as f:
    f.write(hook_js)
print(f"✓ 创建: {hook_js_path}")

# 创建package.json
package_json = {
    "name": "brain-hook",
    "version": "1.0.0",
    "description": "Brain决策流程Hook插件",
    "main": "index.js",
    "openclaw": {
        "type": "hook",
        "events": ["agent.request.pre", "agent.request.post"]
    }
}

package_path = os.path.join(hook_dir, 'package.json')
with open(package_path, 'w', encoding='utf-8') as f:
    json.dump(package_json, f, indent=2)
print(f"✓ 创建: {package_path}")

print("\n" + "=" * 70)
print("Brain API服务器")
print("=" * 70)

print("""
需要启动Brain API服务器:

位置: workspace-工程师/brain_api_server.py
端口: 5000

API接口:
  POST /decide    - 决策接口
  POST /feedback  - 反馈接口
""")