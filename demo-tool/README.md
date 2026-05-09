# Rewriting Tool - 指令重写与执行工具

> 通过配置表定义状态机行为，用户只需编辑 `config.json` 即可定制工具逻辑

## 功能

将用户指令以不同方式、口吻、角度重新表达，然后执行重写后的指令。

## 使用方式

```bash
# 命令行运行
python -m demo-tool.src --input "帮我写一封请假邮件"

# 或直接运行
cd demo-tool/src
python rewriting_tool.py --input "帮我写一封请假邮件"
```

## 配置说明

编辑 `config.json` 即可修改工具行为：

| 字段 | 说明 |
|------|------|
| `model_type` | 使用的模型类型（如 `general`、`inference`） |
| `states` | 状态定义，包含描述、提示词、流转目标 |

### 状态配置示例

```json
{
  "REWRITING": {
    "description": "重新表达用户指令",
    "system_prompt": "你是一个指令改写专家...",
    "transition_to": "EXECUTING"
  },
  "EXECUTING": {
    "description": "执行重写后的指令",
    "system_prompt": "你是一个任务执行助手...",
    "transition_to": "COMPLETED"
  }
}
```

## 目录结构

```
demo-tool/
├── config.json          # 配置文件（定义状态机）
├── src/
│   ├── __init__.py     # 包入口
│   └── rewriting_tool.py  # 工具实现
└── README.md
```

## 依赖

- base_engine（项目公共组件）
- engine/config.json（LLM 模型配置）
