// 我的页逻辑
const app = getApp()

// 模式标签映射
const modeLabelMap = {
  colorize: '黑白上色',
  repair: '破损修复',
  enhance: '清晰度增强',
  denoise: '智能去噪'
}

Page({
  data: {
    userInfo: null,
    historyList: [],
    historyCount: 0,
    savedCount: 0,
    menuList: [
      { icon: '🏠', label: '关于我们' },
      { icon: '❓', label: '使用帮助' },
      { icon: '💬', label: '意见反馈' },
      { icon: '⚙️', label: '设置' }
    ]
  },

  onLoad() {
    this.loadUserInfo()
    this.loadHistory()
    this.loadSavedCount()
  },

  onShow() {
    this.loadHistory()
    this.loadSavedCount()
  },

  // 加载用户信息
  loadUserInfo() {
    const userInfo = app.globalData.userInfo
    this.setData({ userInfo })
  },

  // 加载修复历史
  loadHistory() {
    const history = wx.getStorageSync('restorationHistory') || []
    // 补充模式标签
    const historyList = history.map(item => ({
      ...item,
      modeLabel: modeLabelMap[item.mode] || item.mode,
      fileName: item.fileName || '未命名照片'
    }))
    this.setData({
      historyList,
      historyCount: history.length
    })
  },

  // 加载收藏数量
  loadSavedCount() {
    const saved = wx.getStorageSync('savedItems') || []
    this.setData({ savedCount: saved.length })
  },

  // 跳转到修复页
  navigateToRestore() {
    wx.switchTab({
      url: '/pages/restore/restore'
    })
  },

  // 预览历史图片
  onPreviewHistory(e) {
    const index = e.currentTarget.dataset.index
    const item = this.data.historyList[index]
    if (item && item.image) {
      wx.previewImage({
        current: item.image,
        urls: [item.image]
      })
    }
  },

  // 删除单条历史记录
  onDeleteHistory(e) {
    const index = e.currentTarget.dataset.index
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条修复记录吗？',
      confirmColor: '#C47B5A',
      success: (res) => {
        if (res.confirm) {
          const historyList = this.data.historyList.filter((_, i) => i !== index)
          const storageHistory = historyList.map(item => ({
            id: item.id,
            image: item.image,
            mode: item.mode,
            fileName: item.fileName,
            time: item.time,
            date: item.date
          }))
          wx.setStorageSync('restorationHistory', storageHistory)
          app.globalData.restorationHistory = storageHistory
          this.setData({
            historyList,
            historyCount: historyList.length
          })
          wx.showToast({
            title: '已删除',
            icon: 'success'
          })
        }
      }
    })
  },

  // 清空所有历史记录
  onClearAll() {
    if (this.data.historyList.length === 0) return
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有修复记录吗？此操作不可恢复。',
      confirmColor: '#C47B5A',
      success: (res) => {
        if (res.confirm) {
          wx.setStorageSync('restorationHistory', [])
          app.globalData.restorationHistory = []
          this.setData({
            historyList: [],
            historyCount: 0
          })
          wx.showToast({
            title: '已清空',
            icon: 'success'
          })
        }
      }
    })
  },

  // 菜单项点击
  onMenuTap(e) {
    const label = e.currentTarget.dataset.label
    wx.showToast({
      title: '功能开发中...',
      icon: 'none'
    })
  }
})
