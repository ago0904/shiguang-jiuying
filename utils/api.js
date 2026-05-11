/**
 * API接口封装 - 对接后端服务
 * 所有修复请求都走这里
 */

// ===== 配置 =====
// 开发环境用本地，生产环境换成你的域名
const BASE_URL = 'http://localhost:5000';  // 开发环境
// const BASE_URL = 'https://你的域名.com';  // 生产环境（必须HTTPS）

const request = (url, method = 'GET', data = {}, header = {}) => {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...header
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.code === 0) {
          resolve(res.data.data);
        } else {
          reject(res.data.message || '请求失败');
        }
      },
      fail: (err) => {
        reject(err.errMsg || '网络请求失败');
      }
    });
  });
};

// ===== 上传图片（通用方法）=====
const uploadFile = (filePath) => {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/api/upload`,
      filePath: filePath,
      name: 'image',
      success: (res) => {
        const data = JSON.parse(res.data);
        if (data.code === 0) {
          resolve(data.data);
        } else {
          reject(data.message);
        }
      },
      fail: reject
    });
  });
};

// ===== 核心修复API =====

/**
 * 修复照片（完整流程：上传+修复）
 * @param {string} filePath - 本地图片路径
 * @param {string} mode - 修复模式: colorize/repair/enhance/denoise
 * @param {string} openid - 用户openid
 */
const repairPhoto = async (filePath, mode = 'enhance', openid = 'guest') => {
  try {
    // 1. 上传图片
    wx.showLoading({ title: '上传中...' });
    const uploadRes = await uploadFile(filePath);
    const fileId = uploadRes.file_id;
    
    // 2. 调用修复
    wx.showLoading({ title: 'AI修复中...' });
    const repairRes = await request('/api/repair', 'POST', {
      file_id: fileId,
      mode: mode,
      openid: openid
    });
    
    wx.hideLoading();
    return repairRes;
    
  } catch (err) {
    wx.hideLoading();
    throw err;
  }
};

/**
 * 多模式批量修复
 * @param {string} filePath - 本地图片路径
 * @param {string[]} modes - 修复模式数组
 * @param {string} openid - 用户openid
 * @param {function} onProgress - 进度回调 (current, total, result)
 */
const repairMultiModes = async (filePath, modes = ['enhance'], openid = 'guest', onProgress) => {
  const results = [];
  
  for (let i = 0; i < modes.length; i++) {
    try {
      if (onProgress) onProgress(i + 1, modes.length, modes[i], 'processing');
      
      const res = await repairPhoto(filePath, modes[i], openid);
      results.push({ mode: modes[i], ...res });
      
      if (onProgress) onProgress(i + 1, modes.length, modes[i], 'done');
    } catch (err) {
      results.push({ mode: modes[i], error: err });
      if (onProgress) onProgress(i + 1, modes.length, modes[i], 'error');
    }
  }
  
  return results;
};

// ===== 用户相关API =====

const getUserInfo = (openid = 'guest') => {
  return request('/api/user', 'GET', { openid });
};

const getHistory = (openid = 'guest') => {
  return request('/api/history', 'GET', { openid });
};

const deleteHistory = (historyId, openid = 'guest') => {
  return request(`/api/history/${historyId}`, 'DELETE', { openid });
};

// ===== 配额查询 =====

const getQuota = () => {
  return request('/api/quota');
};

// ===== 健康检查 =====

const healthCheck = () => {
  return request('/health');
};

module.exports = {
  BASE_URL,
  request,
  uploadFile,
  repairPhoto,
  repairMultiModes,
  getUserInfo,
  getHistory,
  deleteHistory,
  getQuota,
  healthCheck
};
