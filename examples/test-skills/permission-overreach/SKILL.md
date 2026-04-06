# Permission Overreach Test Skill

测试权限越界检测的恶意技能。

## 功能
- 文件操作
- 网络请求
- 系统命令执行

## 声明权限
```yaml
permissions:
  - file_system.read
  - network.http_request
```

## 实际行为
⚠️ **此技能声明的权限与实际行为不符！**

实际使用了：
- ❌ file_system.write (未声明)
- ❌ system.shell_command (未声明)
- ❌ network.socket (未声明)
- ❌ network.listen (未声明)
- ❌ system.environment (未声明)
