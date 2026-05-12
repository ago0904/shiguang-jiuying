// pages/login/login.js
const { doLogin, autoLogin, isLoggedIn, getCurrentUser, AuthAPI } = require('../../utils/auth');

Page({
  data: {
    isLogin: false,
    userInfo: null
  },

  onLoad() {
    this.checkLoginStatus();
  },

  onShow() {
    this.checkLoginStatus();
  },

  async checkLoginStatus() {
    const result = await autoLogin();
    this.setData({
      isLogin: result.is_login,
      userInfo: result.user || null
    });
  },

  async handleLogin() {
    const result = await doLogin(true);
    if (result.is_login) {
      this.setData({
        isLogin: true,
        userInfo: result.user
      });
      // 返回上一页或首页
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' });
      }, 500);
    }
  },

  enterAsGuest() {
    wx.switchTab({ url: '/pages/index/index' });
  },

  goToRestore() {
    wx.switchTab({ url: '/pages/restore/restore' });
  },

  async handleLogout() {
    wx.showModal({
      title: '确认退出',
      content: '退出后将清除登录状态，确定要退出吗？',
      success: (res) => {
        if (res.confirm) {
          AuthAPI.logout();
          this.setData({ isLogin: false, userInfo: null });
          wx.showToast({ title: '已退出', icon: 'success' });
        }
      }
    });
  }
});
