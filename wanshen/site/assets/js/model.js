/* ============================================================
 * 网申模拟系统 · 数据模型 + 校验引擎
 * 依据国家电网招聘平台网申填报规则
 * ============================================================ */

/* ---------------- 表单数据模型 ---------------- */
window.EMPTY_DATA = {
  basic: {
    name: '', gender: '', idcard: '', birthday: '',
    gradDate: '', nation: '', nativeProv: '', nativeCity: '', nativeDist: '',
    birthProv: '', birthCity: '', birthDist: '',
    height: '', gradType: '', marital: '', weight: '',
    healthy: '', political: '', veteran: '', xjCode: '',
    intention: [], photo: ''          // photo: base64
  },
  contact: {
    phone: '', tel: '', email: '', addr: '', zip: '', wechat: '', qq: ''
  },
  education: [],      // {from,to,level,school,major,fullTime,highest}
  family: [],         // {title,name,unit,position,phone,addr}
  language: [],       // {type,level,score,date}
  computer: [],       // {level,cert,certNo,date}
  certificate: [],    // {type,name,no,date,org}
  practice: [],       // {from,to,org,dept,position,desc}
  paper: [],          // {title,level,journal,date,authors,rank}
  research: [],       // {name,role,org,from,to,desc}
  award: [],          // {name,level,type,date,org}
  attachment: [],     // {name,type,file,size}
  other: ''           // 其他情况说明
};

/* ---------------- 通用校验工具 ---------------- */
const V = {
  notEmpty: v => !!String(v == null ? '' : v).trim(),

  /* 身份证：18位，校验码算法 */
  idcard(v) {
    const s = String(v || '').trim().toUpperCase();
    if (!s) return '请填写身份证号';
    if (!/^\d{17}[\dX]$/.test(s)) return '身份证号应为18位，最后一位为数字或X';
    const w = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
    const chk = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'];
    let sum = 0;
    for (let i = 0; i < 17; i++) sum += parseInt(s[i], 10) * w[i];
    if (chk[sum % 11] !== s[17]) return '身份证号校验位不正确，请核对';
    // 出生日期合法性
    const b = s.substr(6, 8);
    const y = +b.substr(0, 4), m = +b.substr(4, 2), d = +b.substr(6, 2);
    if (y < 1940 || y > 2012) return '身份证号中的出生年份异常（' + y + '年）';
    if (m < 1 || m > 12) return '身份证号中的出生月份异常';
    if (d < 1 || d > 31) return '身份证号中的出生日期异常';
    return '';
  },

  /* 从身份证解出生日期 */
  idcardBirth(v) {
    const s = String(v || '').trim();
    if (s.length < 14) return '';
    const b = s.substr(6, 8);
    if (!/^\d{8}$/.test(b)) return '';
    return b.substr(0, 4) + '-' + b.substr(4, 2) + '-' + b.substr(6, 2);
  },

  /* 从身份证解性别 */
  idcardGender(v) {
    const s = String(v || '').trim();
    if (s.length < 17) return '';
    const n = parseInt(s[16], 10);
    if (isNaN(n)) return '';
    return n % 2 === 1 ? '男' : '女';
  },

  /* 手机号 */
  phone(v) {
    const s = String(v || '').trim();
    if (!s) return '请填写手机号码';
    if (!/^1[3-9]\d{9}$/.test(s)) return '手机号格式不正确（11位，1开头）';
    return '';
  },

  /* 固定电话（选填，填了才校验） */
  tel(v) {
    const s = String(v || '').trim();
    if (!s) return '';
    if (!/^(\d{3,4}-)?\d{7,8}$/.test(s)) return '座机格式如 010-84621111';
    return '';
  },

  /* 邮箱 */
  email(v) {
    const s = String(v || '').trim();
    if (!s) return '请填写电子邮箱';
    if (!/^[\w.!#$%&'*+/=?^`{|}~-]+@[\w-]+(\.[\w-]+)+$/.test(s)) return '邮箱格式不正确';
    return '';
  },

  /* 邮编 */
  zip(v) {
    const s = String(v || '').trim();
    if (!s) return '请填写邮政编码';
    if (!/^\d{6}$/.test(s)) return '邮政编码为6位数字';
    return '';
  },

  /* 学籍验证码 */
  xjCode(v) {
    const s = String(v || '').trim();
    if (!s) return '请填写学籍验证码';
    if (s.length < 8) return '学籍验证码位数不足（通常为12位以上）';
    if (!/^[A-Za-z0-9]+$/.test(s)) return '学籍验证码仅含字母和数字';
    return '';
  },

  /* 身高 */
  height(v) {
    const s = String(v || '').trim();
    if (!s) return '请填写身高';
    const n = Number(s);
    if (!/^\d{2,3}(\.\d)?$/.test(s) || isNaN(n)) return '身高请填写数字（cm）';
    if (n < 130 || n > 230) return '身高应在 130~230cm 之间';
    return '';
  },

  /* 体重 */
  weight(v) {
    const s = String(v || '').trim();
    if (!s) return '请填写体重';
    const n = Number(s);
    if (!/^\d{2,3}(\.\d)?$/.test(s) || isNaN(n)) return '体重请填写数字（kg）';
    if (n < 30 || n > 200) return '体重应在 30~200kg 之间';
    return '';
  },

  /* 日期格式 YYYY-MM-DD */
  date(v, label) {
    const s = String(v || '').trim();
    if (!s) return '请选择' + (label || '日期');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return '日期格式应为 YYYY-MM-DD';
    return '';
  },

  /* 必填 */
  required(v, label) {
    if (!V.notEmpty(v)) return '请填写' + (label || '此项');
    return '';
  },

  /* 下拉必选 */
  pick(v, label) {
    if (!V.notEmpty(v)) return '请选择' + (label || '此项');
    return '';
  }
};

/* ---------------- 字段规则表 ---------------- */
/* 每条：{ path, label, req, fn } —— fn(val, data) 返回错误消息 */
window.RULES = [
  /* ---- 基本信息 ---- */
  { path: 'basic.name', label: '姓名', req: 1,
    fn: v => !V.notEmpty(v) ? '请填写姓名' : (!/^[\u4e00-\u9fa5·]{2,15}$/.test(v.trim()) ? '姓名应为2~15个汉字' : '') },
  { path: 'basic.gender', label: '性别', req: 1, fn: v => V.pick(v, '性别') },
  { path: 'basic.idcard', label: '身份证号', req: 1, fn: (v, d) => V.idcard(v) },
  { path: 'basic.birthday', label: '出生日期', req: 1,
    fn: (v, d) => {
      const e = V.date(v, '出生日期');
      if (e) return '请填写出生日期';
      const idb = V.idcardBirth(d.basic.idcard);
      if (idb && idb !== v) return '出生日期与身份证号不一致（身份证为 ' + idb + '）';
      return '';
    } },
  { path: 'basic.gradDate', label: '毕业时间', req: 1,
    fn: v => { const e = V.date(v, '毕业时间'); return e ? '请填写预计毕业时间' : ''; } },
  { path: 'basic.nation', label: '民族', req: 1, fn: v => V.pick(v, '民族') },
  { path: 'basic.nativeProv', label: '籍贯', req: 1, fn: v => V.pick(v, '籍贯省份') },
  { path: 'basic.birthProv', label: '生源地', req: 1, fn: v => V.pick(v, '生源地省份') },
  { path: 'basic.height', label: '身高', req: 1, fn: v => V.height(v) },
  { path: 'basic.gradType', label: '毕业生类型', req: 1, fn: v => V.pick(v, '毕业生类型') },
  { path: 'basic.marital', label: '婚姻状况', req: 1, fn: v => V.pick(v, '婚姻状况') },
  { path: 'basic.weight', label: '体重', req: 1, fn: v => V.weight(v) },
  { path: 'basic.political', label: '政治面貌', req: 1, fn: v => V.pick(v, '政治面貌') },
  { path: 'basic.veteran', label: '是否退役军人', req: 1, fn: v => V.pick(v, '是否退役军人') },
  { path: 'basic.xjCode', label: '学籍验证码', req: 1, fn: v => V.xjCode(v) },
  { path: 'basic.photo', label: '证件照', req: 1, fn: v => !V.notEmpty(v) ? '请上传证件照' : '' },

  /* ---- 联系方式 ---- */
  { path: 'contact.phone', label: '手机号码', req: 1, fn: v => V.phone(v) },
  { path: 'contact.tel', label: '座机', req: 0, fn: v => V.tel(v) },
  { path: 'contact.email', label: '电子邮箱', req: 1, fn: v => V.email(v) },
  { path: 'contact.addr', label: '通信地址', req: 1,
    fn: v => !V.notEmpty(v) ? '请填写通信地址' : (v.trim().length < 5 ? '通信地址过短，请填写详细地址' : '') },
  { path: 'contact.zip', label: '邮政编码', req: 1, fn: v => V.zip(v) },
  { path: 'contact.wechat', label: '微信号', req: 0,
    fn: v => { if (!V.notEmpty(v)) return ''; return /^[a-zA-Z][\w-]{5,19}$/.test(v.trim()) ? '' : '微信号以字母开头，6~20位'; } },
  { path: 'contact.qq', label: 'QQ号', req: 0,
    fn: v => { if (!V.notEmpty(v)) return ''; return /^[1-9]\d{4,11}$/.test(v.trim()) ? '' : 'QQ号应为5~12位数字'; } }
];

/* ---------------- 取/设路径值 ---------------- */
window.getPath = function (obj, path) {
  return path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
};
window.setPath = function (obj, path, val) {
  const ks = path.split('.');
  let o = obj;
  for (let i = 0; i < ks.length - 1; i++) { if (o[ks[i]] == null) o[ks[i]] = {}; o = o[ks[i]]; }
  o[ks[ks.length - 1]] = val;
};
