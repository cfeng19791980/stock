# 查找并修改渲染函数
$filepath = "e:\csi10\index.html"
$content = Get-Content $filepath -Raw

# 查找renderStockPool函数起始位置
$pattern = "function renderStockPool\(stocks\) \{"
$match = [regex]::Match($content, $pattern)

if ($match.Success) {
    $startPos = $match.Index
    # 找到函数结束位置（下一个function关键字）
    $endPattern = "function renderBuyList"
    $endMatch = [regex]::Match($content.Substring($startPos), $endPattern)
    
    if ($endMatch.Success) {
        $funcEnd = $startPos + $endMatch.Index
        
        # 提取原函数
        $oldFunc = $content.Substring($startPos, $funcEnd - $startPos)
        
        Write-Output "找到renderStockPool函数:"
        Write-Output "起始: $startPos"
        Write-Output "结束: $funcEnd"
        Write-Output "长度: $($funcEnd - $startPos)"
    }
}

# 查找renderBuyList函数
$pattern2 = "function renderBuyList\(stocks\) \{"
$match2 = [regex]::Match($content, $pattern2)
if ($match2.Success) {
    Write-Output "\n找到renderBuyList函数起始: $($match2.Index)"
}

# 查找renderSellList函数
$pattern3 = "function renderSellList\(stocks\) \{"
$match3 = [regex]::Match($content, $pattern3)
if ($match3.Success) {
    Write-Output "\n找到renderSellList函数起始: $($match3.Index)"
}