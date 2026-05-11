App({
  globalData: {
    userInfo: null,
    restorationHistory: [],
    galleryData: [
      { id: 1, title: '1960s全家福', mode: 'colorize', date: '2025-04-12', image: '/images/gallery-1.jpg' },
      { id: 2, title: '70年代好友合影', mode: 'enhance', date: '2025-04-10', image: '/images/gallery-2.jpg' },
      { id: 3, title: '传统茶馆老照片', mode: 'colorize', date: '2025-04-08', image: '/images/gallery-3.jpg' },
      { id: 4, title: '80年代童年记忆', mode: 'repair', date: '2025-04-05', image: '/images/gallery-4.jpg' },
      { id: 5, title: '修复的结婚照', mode: 'repair', date: '2025-04-03', image: '/images/gallery-5.jpg' },
      { id: 6, title: '90年代街景', mode: 'denoise', date: '2025-04-01', image: '/images/gallery-6.jpg' }
    ]
  },

  onLaunch() {
    console.log('拾光旧影 小程序启动')
    this.loadHistory()
  },

  loadHistory() {
    const history = wx.getStorageSync('restorationHistory') || []
    this.globalData.restorationHistory = history
  },

  addToHistory(item) {
    const history = this.globalData.restorationHistory
    history.unshift(item)
    if (history.length > 50) history.pop()
    this.globalData.restorationHistory = history
    wx.setStorageSync('restorationHistory', history)
  }
})