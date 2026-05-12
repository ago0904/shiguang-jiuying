const { autoLogin, isLoggedIn, getCurrentUser } = require('./utils/auth');

App({
  globalData: {
    userInfo: null,
    isLogin: false,
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

  async onLaunch() {
    console.log('拾光旧影 小程序启动')
    this.loadHistory()
    
    // 自动登录
    const result = await autoLogin();
    this.globalData.isLogin = result.is_login;
    this.globalData.userInfo = result.user || null;
    console.log('登录状态:', result.is_login ? '已登录' : '未登录');
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
  },

  // 更新登录状态
  setLoginState(isLogin, userInfo) {
    this.globalData.isLogin = isLogin;
    this.globalData.userInfo = userInfo;
  },

  // 检查是否登录（未登录则跳转登录页）
  checkLogin() {
    if (!this.globalData.isLogin) {
      wx.navigateTo({ url: '/pages/login/login' });
      return false;
    }
    return true;
  }
})