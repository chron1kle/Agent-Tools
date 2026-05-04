# Agent Logger 架构设计

> **版本**: 1.0
> **说明**: Agent Tools 日志系统的跨语言架构设计

---

## 一、设计目标

1. **语言无关** - 不同语言有对应实现，但接口一致
2. **零侵入** - 用户只需配置端口，其他交给组件
3. **可追溯** - 所有日志实时输出，支持多客户端监听

---

## 二、核心思路

```
┌──────────────────────────────────────────────────────────┐
│                      Agent Tool                          │
│                                                          │
│   @Logger(port=8765)          # 注解/装饰器/宏          │
│   class MyTool {               #                        │
│       func extract()           #   日志自动输出         │
│   }                            #                        │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ TCP Server   │
                    │ (localhost)  │◀── telnet/nc/客户端
                    │   port:8765  │
                    └──────────────┘
```

用户配置：
```json
{
  "log": {
    "enabled": true,
    "host": "localhost",
    "port": 8765,
    "level": "INFO"
  }
}
```

使用：
```python
@Logger(port=8765)
class PDFTool:
    def extract(self, path):
        self.log.info("extract start", {"path": path})
        # ...
```

---

## 三、跨语言实现方案

### 3.1 Python

使用装饰器 + 上下文管理器：

```python
# 使用方式
@Logger(config={"port": 8765})
class MyTool:
    def extract(self, path):
        self.log.info("start", {"path": path})

# 装饰器实现（简化）
def Logger(config):
    def decorator(cls):
        original_init = cls.__init__
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._logger = SocketLogger(config)
        cls.log = property(lambda self: self._logger)
        return cls
    return decorator
```

### 3.2 Node.js

使用装饰器：

```typescript
@Logger({ port: 8765 })
class PDFTool {
  @Log({ event: "extract_start" })
  extract(path: string) {
    // this.log.info(...)
  }
}
```

### 3.3 Go

使用代码生成（因为无注解）：

```go
//go:generate logger-gen -port=8765

// 生成的代码会自动添加日志字段和方法
type PDFTool struct {
    log *Logger
}

func (t *PDFTool) Extract(path string) {
    t.log.Info("extract start", "path", path)
}
```

生成命令：
```bash
go generate ./...
```

### 3.4 Rust

使用宏：

```rust
#[logger(port = 8765)]
struct PDFTool {
    // 字段
}

impl PDFTool {
    fn extract(&self, path: &str) {
        self.log().info("extract start", &[("path", path)]);
    }
}
```

---

## 四、输出格式

### 4.1 JSON 格式（默认）

```json
{
  "timestamp": "2026-05-05T00:18:00",
  "level": "INFO",
  "event": "extract_start",
  "message": "开始提取PDF",
  "data": {
    "path": "/path/to/file.pdf"
  }
}
```

### 4.2 客户端接收示例

```bash
# telnet
$ telnet localhost 8765
{"timestamp":"2026-05-05T00:18:00","level":"INFO","event":"extract_start",...}

# nc
$ nc localhost 8765
{"timestamp":"2026-05-05T00:18:00","level":"INFO","event":"extract_start",...}

# 编程
import socket
s = socket.socket()
s.connect(("localhost", 8765))
while True:
    print(s.recv(1024).decode())
```

---

## 五、日志级别

| 级别 | 说明 |
|------|------|
| DEBUG | 调试信息 |
| INFO | 正常流程 |
| WARNING | 警告 |
| ERROR | 错误 |

---

## 六、配置项

```json
{
  "log": {
    "enabled": true,
    "host": "localhost",
    "port": 8765,
    "level": "INFO",
    "format": "json"
  }
}
```

---

## 七、组件目录结构

```
common/logger/
├── README.md           # 本文档
├── python/             # Python 实现
│   ├── __init__.py
│   ├── decorator.py
│   └── server.py
├── nodejs/            # Node.js 实现
│   ├── index.ts
│   └── decorator.ts
├── go/                # Go 实现
│   ├── logger.go
│   └── cmd/
└── rust/              # Rust 实现
    ├── lib.rs
    └── macro.rs
```

---

## 八、设计原则

1. **配置外部化** - 端口等配置从 config.json 读取
2. **TCP 广播** - 多客户端可同时监听
3. **向后兼容** - 不影响原有日志（如 print/console.log）
4. **优雅降级** - 如果端口被占用，可选择其他端口或跳过日志

---

**最后更新**: 2026-05-05
