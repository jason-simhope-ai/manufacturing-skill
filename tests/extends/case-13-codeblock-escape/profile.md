---
name: subject
extends: core/agents/subject
---

<!-- inherit -->

## Documentation: how to use inheritance

範例：profile 檔內這樣寫：

```markdown
<!-- inherit -->

## 新章節
```

The fenced block above contains a `<!-- inherit -->` that must be
treated as documentation, not a directive. Only the real one above
this section counts.
