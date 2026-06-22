# 空调建筑节能研究型搜索智能体

这是一个最短闭环的真实联网搜索原型：

用户输入关键词 -> 真实搜索 -> 结果筛选排序 -> 单跳读取网页正文 -> 生成总结小报 -> Streamlit 展示。

## 启动

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## 命令行测试

```powershell
python run_test.py
```

## 约束说明

- 未使用 sitemap、站内递进、BFS/DFS、动态站点发现或全站爬虫。
- 未读取本地 txt/doc/json/PDF 作为搜索内容来源。
- 未使用固定 URL 结果池；搜索 query 会进入真实搜索入口并影响排序与总结。
