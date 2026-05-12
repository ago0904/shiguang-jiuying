Component({
  /**
   * 组件的属性列表
   */
  properties: {

  },

  /**
   * 组件的初始数据
   */
  data: {
    active: false
  },

  /**
   * 组件的方法列表
   */
  methods: {
    onTap() {
      this.triggerEvent('choose');
    },

    onTouchStart() {
      this.setData({ active: true });
    },

    onTouchEnd() {
      this.setData({ active: false });
    }
  }
});
