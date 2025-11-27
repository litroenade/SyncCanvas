## 1. 语言约定
- **所有对话、注释、文档、提交信息** 一律使用 **简体中文**。

## 2. 环境信息
- 操作系统：`Windows 10/11`
- 默认终端：`PowerShell`
- 行尾序列：`CRLF`
- 默认编码：`UTF-8`（如项目已有 `.editorconfig` 则从其约定）
- 每行代码长度 ≤ 120 字符（Python Black 默认）。
- Windows 路径请使用 原始字符串 或 正斜杠 避免转义问题：r"C:/path" 或 "C:/path"。

## 3. 代码注释规范
请在 **任何层级的代码** 中按以下优先级添加对应注释；如无特殊需求，采用 Google-Style 中文注释模板。

| 层级        | 注释触发条件 & 位置               | 模板（中文） |
|-------------|----------------------------------|--------------|
| **项目级**   | 项目根目录 README / docs/index.md | `# 项目名称`  <br>`## 项目简介` <br>`## 快速开始` |
| **包级**     | 每个 `__init__.py` 顶部           | `"""包名称：xxx  <br>功能说明：yyy"""` |
| **模块级**   | `.py` / `.ts` / `.vue` 文件顶部   | `"""模块名称：xxx  <br>主要功能：yyy"""` |
| **文件级**   | 任意源码文件顶部（非模块语言）    | @Time: {date} {time}<br>@Author: Yang208115<br>@File: {filename}<br>@Desc: 作用说明 |
| **类级**     | 每个 class 定义前                 | `"""[类的单行摘要]<br><br>Attributes:<br>    [属性名] ([类型]): [属性描述]"""` |
| **函数级**   | 每个 def / function / method 前   | Google-Style Docstring（见下方示例） |
| **代码级**   | 复杂/关键算法、魔法值、正则等     | 行尾 `# 说明` 或 `/* 说明 */` |

### 3.1 Python 函数级 Docstring 模板
```python
def fetch_user(uid: int) -> User:
    """根据用户 ID 获取用户对象。

    Args:
        uid: 用户唯一标识。

    Returns:
        User: 完整的用户模型实例。

    Raises:
        ValueError: 当 uid 小于等于 0 时抛出。
    """
```

### 3.2 TypeScript / JavaScript 函数级 JSDoc 模板
```typescript
/**
 * 根据用户 ID 获取用户对象
 * @param uid - 用户唯一标识
 * @returns 完整的用户对象
 * @throws 当 uid 小于等于 0 时抛出错误
 */
function fetchUser(uid: number): User {}
```

## 4.命名规则
- 项目名 kebab_case，全小写
- 包名、模块名、文件名 snake_case，全小写
- 类名 PascalCase
- 函数/方法/变量名 snake_case
- 常量名 UPPER_SNAKE_CASE
- TypeScript/JavaScript 私有变量前缀下划线 _camelCase

## 5.自动生成要求
- 当我请求「生成代码」「补全文件」「新建模块」时，务必一次性输出带全层级注释的完整代码。
- 若文件已存在，先读取原文件，再追加缺失注释，而不是覆盖。
- 优先遵循项目已有的 .editorconfig , linter, formatter 等配置文件。若无配置，则严格遵循本规则。

## 6.提交/文档语言
- commit message、Pull Request、Issue、README 一律用中文。
- 示例：feat: 添加用户登录接口

## 7.其他偏好
- 使用单引号 '（JavaScript/TypeScript）或双引号 "（Python）保持一致即可。
- 写代码不要使用或出现emoji以及√等unicore字符

### 类定义和命名

1. 所有的类名称需要使用**大驼峰命名法**进行命名。
2. 所有**类属性（常量、变量）\**均需\**在class层级定义**。
3. 所有类实例属性均需在`__init__`方法中声明并初始化
4. 所有类与函数请尽量使用三引号（`"""`）编写文档注释。

### 变量与常量

1. 常量请使用**全大写**+**下划线**的方式命名，如有可能，请尽量进行类型声明。
2. 变量请使用**全小写**+**下划线**的方式命名，必须进行**类型声明**。

### 异步函数和任务

1. 对于脱离类生命周期的周期性定时任务，请继承`AsyncTask基类`实现定时任务类，并使用`async_task_manager.add_task()`交由异步任务管理器统一管理；
2. 对于类生命周期内的异步任务，请使用`asyncio.create_task()`创建协程处理，并在合适的位置处理异常，并使用`Task.cancel()`和`await`确保任务完成退出；
3. 对于业务逻辑中串行的异步任务，请使用`await`来创建协程处理并阻塞业务逻辑直至任务结束。

### Import 规范

首先我们定义一个“包”：认为每一个直接含有python代码文件的文件夹都是一个包。

1. 所有的`import`语句请放在文件的最上方，除非你需要动态导入某个模块或者`try import`。
2. 对于每个包，包内的文件的互相导入请使用相对路径导入，如`import .config`或者`from .config import Config`。
3. 对于跨包文件导入，请使用绝对路径导入，如`from package.module import Class`。
4. 请使用Ruff检查是否有没有用到的`import`语句，如果有，请删除这条`import`语句。