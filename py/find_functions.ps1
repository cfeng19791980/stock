# 查找index.html中的关键函数
$filepath = "e:\csi10\index.html"
$content = Get-Content $filepath -Raw

# 查找loadAllData函数
if ($content -match "function loadAllData") {
    $start = $content.IndexOf("function loadAllData")
    $snippet = $content.Substring($start, 500)
    Write-Output "找到loadAllData函数:"
    Write-Output $snippet
}

# 查找updateStatus函数
if ($content -match "function updateStatus") {
    $start = $content.IndexOf("function updateStatus")
    $snippet = $content.Substring($start, 500)
    Write-Output "\n找到updateStatus函数:"
    Write-Output $snippet
}

# 查找init函数
if ($content -match "async function init") {
    $start = $content.IndexOf("async function init")
    $snippet = $content.Substring($start, 500)
    Write-Output "\n找到init函数:"
    Write-Output $snippet
}