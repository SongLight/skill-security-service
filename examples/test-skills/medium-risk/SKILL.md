# Medium Risk Skill - 中等风险技能

这是一个包含中等风险问题的技能，用于测试扫描器对中等风险的检测。

## 声明权限
```yaml
permissions:
  - file_system.read
  - network.http_request
```

## 实际行为
⚠️ **存在未声明的中等风险操作：**

### 1. 文件写入（未声明）
- 创建临时文件
- 写入日志文件

### 2. 环境变量访问（未声明）
- 读取 `PATH`
- 读取 `HOME`

### 3. 数据库访问（未声明）
- SQLite 连接

## 风险等级
🟡 **MEDIUM** - 需要审查和修复
