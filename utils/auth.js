/**
 * 微信登录 + JWT Token 管理
 * 全局用户状态管理
 */

const API_BASE = 'https://你的后端域名.com';  // 替换为实际后端地址

// ===== Token 管理 =====
const TokenManager = {
  get() {
    return wx.getStorageSync('jwt_token') || '';
  },
  set(token) {
    wx.setStorageSync('jwt_token', token);
  },
  clear() {
    wx.removeStorageSync('jwt_token');
    wx.removeStorageSync('user_info');
  },
  has() {
    return !!this.get();
  }
};

// ===== 用户信息管理 =====
const UserManager = {
  get() {
    return wx.getStorageSync('user_info') || null;
  },
  set(user) {
    wx.setStorageSync('user_info', user);
  },
  clear() {
    wx.removeStorageSync('user_info');
  }
};

// ===== 微信登录 =====
const wxLogin = () => {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (res) => {
        if (res.code) {
          resolve(res.code);
        } else {
          reject(res.errMsg || '登录失败');
        }
      },
      fail: reject
    });
  });
};

// ===== 后端认证 =====
const AuthAPI = {
  /**
   * 微信登录 - 小程序code换token
   */
  async loginWithWechat(code, userInfo = null) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${API_BASE}/api/auth/login`,
        method: 'POST',
        data: {
          code: code,
          user_info: userInfo  // 可选：用户信息（需用户授权）
        },
        success: (res) => {
          if (res.statusCode === 200 && res.data.code === 0) {
            const { token, user } = res.data.data;
            TokenManager.set(token);
            UserManager.set(user);
            resolve({ token, user });
          } else {
            reject(res.data.message || '登录失败');
          }
        },
        fail: reject
      });
    });
  },

  /**
   * 检查登录状态
   */
  async checkLogin() {
    return new Promise((resolve, reject) => {
      const token = TokenManager.get();
      if (!token) {
        resolve({ is_login: false });
        return;
      }
      wx.request({
        url: `${API_BASE}/api/auth/check`,
        method: 'GET',
        header: { 'Authorization': `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode === 200 && res.data.code === 0) {
            resolve({ is_login: true, user: res.data.data });
          } else {
            TokenManager.clear();
            UserManager.clear();
            resolve({ is_login: false });
          }
        },
        fail: () => {
          resolve({ is_login: false });
        }
      });
    });
  },

  /**
   * 获取当前用户信息
   */
  async getUserInfo() {
    return new Promise((resolve, reject) => {
      const token = TokenManager.get();
      if (!token) {
        reject('未登录');
        return;
      }
      wx.request({
        url: `${API_BASE}/api/auth/me`,
        method: 'GET',
        header: { 'Authorization': `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode === 200 && res.data.code === 0) {
            UserManager.set(res.data.data);
            resolve(res.data.data);
          } else {
            reject(res.data.message || '获取失败');
          }
        },
        fail: reject
      });
    });
  },

  /**
   * 刷新Token
   */
  async refreshToken() {
    return new Promise((resolve, reject) => {
      const token = TokenManager.get();
      wx.request({
        url: `${API_BASE}/api/auth/refresh`,
        method: 'POST',
        header: { 'Authorization': `Bearer ${token}` },
        success: (res) => {
          if (res.statusCode === 200 && res.data.code === 0) {
            TokenManager.set(res.data.data.token);
            resolve(res.data.data);
          } else {
            reject(res.data.message || '刷新失败');
          }
        },
        fail: reject
      });
    });
  },

  /**
   * 退出登录
   */
  async logout() {
    TokenManager.clear();
    UserManager.clear();
    return true;
  }
};

// ===== 自动登录 =====
const autoLogin = async () => {
  try {
    // 先检查本地token
    const token = TokenManager.get();
    if (!token) {
      return { is_login: false, need_login: true };
    }

    // 检查token有效性
    const check = await AuthAPI.checkLogin();
    if (check.is_login) {
      return { is_login: true, user: check.user };
    }

    // Token过期，尝试重新登录
    const code = await wxLogin();
    const result = await AuthAPI.loginWithWechat(code);
    return { is_login: true, user: result.user };
    
  } catch (err) {
    console.error('自动登录失败:', err);
    return { is_login: false, need_login: true, error: err };
  }
};

// ===== 发起登录 =====
const doLogin = async (getUserProfile = false) => {
  try {
    wx.showLoading({ title: '登录中...' });
    
    // 获取微信code
    const code = await wxLogin();
    
    // 获取用户信息（可选，需用户授权）
    let userInfo = null;
    if (getUserProfile) {
      try {
        const profile = await wx.getUserProfile({ desc: '用于完善用户资料' });
        userInfo = profile.userInfo;
      } catch (e) {
        console.log('用户拒绝授权');
      }
    }
    
    // 后端登录
    const result = await AuthAPI.loginWithWechat(code, userInfo);
    
    wx.hideLoading();
    wx.showToast({ title: '登录成功', icon: 'success' });
    
    return { is_login: true, user: result.user };
    
  } catch (err) {
    wx.hideLoading();
    wx.showToast({ title: '登录失败', icon: 'error' });
    console.error('登录失败:', err);
    return { is_login: false, error: err };
  }
};

// ===== 通用请求封装（自动带Token） =====
const authRequest = (url, method = 'GET', data = {}) => {
  return new Promise((resolve, reject) => {
    const token = TokenManager.get();
    wx.request({
      url: `${API_BASE}${url}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      success: (res) => {
        if (res.statusCode === 401) {
          // Token过期，清除并重新登录
          TokenManager.clear();
          UserManager.clear();
          reject({ code: 401, message: '登录已过期，请重新登录' });
          return;
        }
        if (res.statusCode === 200 && res.data.code === 0) {
          resolve(res.data.data);
        } else {
          reject(res.data.message || '请求失败');
        }
      },
      fail: reject
    });
  });
};

// ===== 检查登录状态（同步） =====
const isLoggedIn = () => {
  return TokenManager.has() && UserManager.get() !== null;
};

// ===== 获取当前用户 =====
const getCurrentUser = () => {
  return UserManager.get();
};

// ===== 导出 =====
module.exports = {
  TokenManager,
  UserManager,
  AuthAPI,
  autoLogin,
  doLogin,
  authRequest,
  isLoggedIn,
  getCurrentUser,
  wxLogin
};
