/* ============================================================
 * 模块 Schema —— 13 个填报模块的字段定义
 * 字段/选项/必填标记依据国网招聘平台真实页面（35张截图）逐一还原
 * 表单由本文件驱动渲染
 * ============================================================ */

window.SCHEMA = [

  /* ===================== 1. 基本信息 ===================== */
  {
    id: 'basic', title: '基本信息', req: true, layout: 'grid-basic',
    fields: [
      { p: 'basic.name', label: '姓名', type: 'text' },
      { p: 'basic.gender', label: '性别', type: 'select', src: 'gender', auto: 'gender' },

      { p: 'basic.idcard', label: '身份证号', type: 'text', max: 18, auto: 'idcard' },
      { p: 'basic.birthday', label: '出生日期', type: 'date', auto: 'birthday' },

      { p: 'basic.gradDate', label: '预计毕业时间', type: 'date' },
      { p: 'basic.nation', label: '民族', type: 'select', src: 'nation' },

      { p: 'basic.nativeProv', label: '籍贯', type: 'region', group: 'native', span: 2 },
      {
        p: 'basic.birthProv', label: '生源地', type: 'region', group: 'birth', span: 2,
        help: '生源地是指学生大学入学前户口所在地'
      },

      { p: 'basic.height', label: '身高（cm）', type: 'text', ph: '', numeric: true },
      { p: 'basic.gradType', label: '毕业生类型', type: 'select', src: 'graduateType' },

      { p: 'basic.marital', label: '婚姻状况', type: 'select', src: 'maritalStatus' },
      { p: 'basic.weight', label: '体重（kg）', type: 'text', numeric: true },

      { p: 'basic.healthy', label: '是否健康', type: 'radio', src: 'yesNo', noReq: true },
      { p: 'basic.political', label: '政治面貌', type: 'select', src: 'politicalStatus' },

      { p: 'basic.veteran', label: '是否退役军人', type: 'radio', src: 'yesNo' },
      { p: 'basic.xjCode', label: '学籍验证码', type: 'text', ph: '请填写有效学籍验证码' },

      { p: 'basic.intention', label: '求职意向', type: 'tags', span: 2, limit: 3, noReq: true,
        help: '求职意向标签仅作为意向收集，最终入职岗位以实际为准' }
    ]
  },

  /* ===================== 2. 联系方式 ===================== */
  {
    id: 'contact', title: '联系方式', req: true, layout: 'grid',
    fields: [
      { p: 'contact.phone', label: '手机号码', type: 'text', max: 11, numeric: true },
      { p: 'contact.tel', label: '座机', type: 'text', ph: '如：010-84621111', noReq: true },
      { p: 'contact.email', label: '电子邮箱', type: 'text' },

      { p: 'contact.addr', label: '通信地址', type: 'text' },
      { p: 'contact.zip', label: '邮政编码', type: 'text', max: 6, numeric: true },
      { p: 'contact.wechat', label: '微信号', type: 'text', ph: '请填写有效的微信号', noReq: true },

      { p: 'contact.qq', label: 'QQ号', type: 'text', noReq: true, numeric: true,
        help: '请谨慎填写联系方式', helpGreen: true }
    ]
  },

  /* ===================== 3. 教育经历 ===================== */
  {
    id: 'education', title: '教育经历', req: true, kind: 'table', cols: 3,
    tips: [
      '教育经历请从高往低填写，高中及以下学历无需填写',
      '1.现阶段教育经历必须填写，并标识为最高学历；',
      '2.研究生必须填写一条本科或专科记录；',
      '3.专升本人员必须填写一条专科记录；',
      '4.双学士学位人员学位必须填写主修、辅修教育经历（"是否辅修学位"应正确标识），且学位均选择"双学士"。'
    ],
    columns: [
      { k: 'range', t: '起止时间', fmt: r => (r.entrance || '') + (r.graduate ? '至' + r.graduate : '') },
      { k: 'lv', t: '学历/学位', fmt: r => (r.level || '') + (r.degree && r.degree !== '无' ? '/' + r.degree : '') },
      { k: 'school', t: '学校名称' },
      { k: 'major', t: '所学专业' },
      { k: 'ft', t: '是否全日制', fmt: r => r.studyForm === '普通全日制' ? '是' : (r.studyForm ? '否' : '') },
      { k: 'highest', t: '是否最高学历' }
    ],
    subFields: [
      { k: 'entrance', label: '入学时间', type: 'date', req: 1, ph: '请输入入学时间' },
      { k: 'graduate', label: '毕业时间', type: 'date', req: 1, ph: '请输入毕业时间' },
      { k: 'studyForm', label: '学习形式', type: 'select', src: 'studyForm', req: 1 },
      { k: 'level', label: '学历', type: 'select', src: 'eduLevelReal', req: 1 },
      { k: 'school', label: '学校名称', type: 'school', req: 1, ph: '请填写学校名称' },
      { k: 'diplomaNo', label: '学历证书号', type: 'text', ph: '请填写学历证书号' },
      { k: 'batch', label: '招生批次', type: 'select', src: 'recruitBatch', req: 1 },
      { k: 'highest', label: '是否最高学历', type: 'select', src: 'highestDegree', req: 1 },
      { k: 'degree', label: '学位', type: 'select', src: 'degreeList', req: 1 },
      { k: 'degreeNo', label: '学位证书号', type: 'text', ph: '请输入学位证书号' },
      { k: 'subjectLevel', label: '学科层次', type: 'select', src: 'subjectLevel' },
      { k: 'major', label: '专业名称', type: 'major', req: 1, ph: '请填写专业名称' },
      { k: 'rankpair', label: '专业排名', type: 'rankpair' },
      { k: 'researchDir', label: '研究方向', type: 'text', ph: '请填写研究方向' },
      { k: 'thesisTitle', label: '毕业论文题目', type: 'text', ph: '请填写毕业论文题目' },
      { k: 'gpa', label: '绩点', type: 'text', ph: '请输入绩点' },
      { k: 'gaokao', label: '是否参加国内高考', type: 'select', src: 'yesNo', req: 1 },
      { k: 'gaokaoScore', label: '高考成绩', type: 'text', num: 1, ph: '请输入高考成绩' },
      { k: 'trainMode', label: '培养方式', type: 'select', src: 'trainMode', req: 1 },
      { k: 'gaokaoPlace', label: '高考所在地', type: 'select', src: 'provinces', req: 1 }
    ]
  },

  /* ===================== 4. 主要家庭成员 ===================== */
  {
    id: 'family', title: '主要家庭成员', req: true, kind: 'table', cols: 3,
    columns: [
      { k: 'title', t: '称谓' }, { k: 'name', t: '姓名' },
      { k: 'unit', t: '工作单位' }, { k: 'position', t: '职务/岗位' },
      { k: 'phone', t: '手机号码' }, { k: 'addr', t: '家庭住址' }
    ],
    subFields: [
      { k: 'title', label: '称谓', type: 'select', src: 'familyTitle', req: 1 },
      { k: 'name', label: '姓名', type: 'text', req: 1, ph: '请填写姓名' },
      { k: 'birth', label: '出生日期', type: 'date', req: 1 },
      { k: 'position', label: '职务/岗位', type: 'text', max: 40, ph: '请输入职务/岗位（40字以内）' },
      { k: 'unit', label: '工作单位', type: 'text', max: 10, ph: '工作单位在10字以内' },
      { k: 'phone', label: '手机号码', type: 'text', num: 1, max: 11, ph: '请填写手机号码' },
      { k: 'addr', label: '家庭住址', type: 'text', ph: '请填写家庭住址' }
    ]
  },

  /* ===================== 5. 外语能力 ===================== */
  {
    id: 'language', title: '外语能力', req: false, kind: 'table', cols: 3,
    columns: [
      { k: 'type', t: '外语语种' }, { k: 'level', t: '外语水平级别' },
      { k: 'proficiency', t: '熟练程度' }, { k: 'certDate', t: '证书获得时间' },
      { k: 'score', t: '成绩' }
    ],
    subFields: [
      { k: 'type', label: '外语语种', type: 'select', src: 'langTypeReal', req: 1 },
      { k: 'level', label: '外语水平级别', type: 'select', src: 'langLevelReal', req: 1,
        help: '外语水平级别是大学英语四级、大学英语六级、英语专业四级、英语专业八级时成绩及其证书编号必须填写' },
      { k: 'proficiency', label: '熟练程度', type: 'select', src: 'proficiency', req: 1 },
      { k: 'certDate', label: '证书获得时间', type: 'date', req: 1, ph: '请填写证书获得时间' },
      { k: 'certOrg', label: '认证机构', type: 'text', req: 1, max: 20, ph: '认证机构名称在20字以内' },
      { k: 'score', label: '成绩', type: 'text', num: 1, ph: '请填写成绩' },
      { k: 'certNo', label: '证书编号', type: 'text', num: 1, ph: '请填写证书编号' },
      { k: 'certFile', label: '上传证书或成绩单', type: 'file', full: true, limit: 1024,
        accept: '.pdf,.doc,.xls,.jpg,.png,.docx,.xlsx' },
      { k: 'remark', label: '其他备注', type: 'textarea', full: true, max: 50,
        ph: '请输入其他需要说明的信息，最多50个字符' }
    ]
  },

  /* ===================== 6. 计算机能力 ===================== */
  {
    id: 'computer', title: '计算机能力', req: false, kind: 'table', cols: 3,
    columns: [
      { k: 'certName', t: '证书名称' }, { k: 'certDate', t: '证书获得时间' },
      { k: 'org', t: '发证单位' }, { k: 'level', t: '级别' }
    ],
    subFields: [
      { k: 'certName', label: '证书名称', type: 'text', req: 1, ph: '请填写证书名称' },
      { k: 'certDate', label: '证书获得时间', type: 'date', req: 1, ph: '请输入证书获得时间' },
      { k: 'org', label: '发证单位', type: 'text', req: 1, max: 20, ph: '发证机构名称在20字以内' },
      { k: 'level', label: '级别', type: 'text', ph: '请填写证书级别' },
      { k: 'score', label: '成绩', type: 'text', num: 1, ph: '请填写成绩' },
      { k: 'certNo', label: '证书编号', type: 'text', num: 1, ph: '请填写证书编号' },
      { k: 'certFile', label: '上传证书', type: 'file', full: true, limit: 1024,
        accept: '.pdf,.doc,.xls,.jpg,.png,.docx,.xlsx' },
      { k: 'remark', label: '其他备注', type: 'textarea', full: true, max: 50,
        ph: '请输入其他需要说明的信息。字数限制为50' }
    ]
  },

  /* ===================== 7. 资格证书 ===================== */
  {
    id: 'certificate', title: '资格证书', req: false, kind: 'table', cols: 3,
    columns: [
      { k: 'certName', t: '证书名称' }, { k: 'certDate', t: '证书获得时间' },
      { k: 'org', t: '发证单位' }, { k: 'level', t: '级别' }
    ],
    subFields: [
      { k: 'certName', label: '证书名称', type: 'text', req: 1, ph: '请填写证书名称' },
      { k: 'certDate', label: '证书获得时间', type: 'date', req: 1, ph: '请输入证书获得时间' },
      { k: 'org', label: '发证单位', type: 'text', req: 1, max: 20, ph: '发证机构名称在20字以内' },
      { k: 'level', label: '级别', type: 'text', ph: '请填写证书级别' },
      { k: 'score', label: '成绩', type: 'text', num: 1, ph: '请填写成绩' },
      { k: 'certNo', label: '证书编号', type: 'text', num: 1, ph: '请填写证书编号' },
      { k: 'certFile', label: '上传证书', type: 'file', full: true, limit: 1024,
        accept: '.pdf,.doc,.xls,.jpg,.png,.docx,.xlsx' },
      { k: 'remark', label: '其他备注', type: 'textarea', full: true, max: 50,
        ph: '请输入其他需要说明的信息。最多50个字符' }
    ]
  },

  /* ===================== 8. 主要社会实践/工作经历 ===================== */
  {
    id: 'practice', title: '主要社会实践/工作经历', req: false, kind: 'table', cols: 3,
    columns: [
      { k: 'range', t: '起止时间', fmt: r => (r.from || '') + (r.to ? '至' + r.to : '') },
      { k: 'unit', t: '单位' }, { k: 'position', t: '职务/岗位' },
      { k: 'workForm', t: '工作形式' }
    ],
    subFields: [
      { k: 'from', label: '开始时间', type: 'date', req: 1, ph: '请输入开始时间' },
      { k: 'to', label: '结束时间', type: 'date', req: 1, ph: '请输入结束时间' },
      { k: 'unit', label: '单位', type: 'text', req: 1, ph: '请填写单位' },
      { k: 'position', label: '职务/岗位', type: 'text', req: 1, max: 40, ph: '请输入职务/岗位（40字以内）' },
      { k: 'workForm', label: '工作形式', type: 'select', src: 'workFormReal', req: 1 },
      { k: 'witness', label: '证明人', type: 'text', ph: '请填写证明人' },
      { k: 'detail', label: '具体工作要点', type: 'textarea', full: true, max: 60,
        ph: '请输入其他需要说明的信息，最多60个字符' }
    ]
  },

  /* ===================== 9. 学术成果-论文 ===================== */
  {
    id: 'paper', title: '学术成果-论文', req: false, kind: 'table', cols: 3,
    tips: ['学术论文成果，建议按照重要级别，从高到低，5条以内。'],
    columns: [
      { k: 'level', t: '论文级别' }, { k: 'title', t: '论文名称' },
      { k: 'pubDate', t: '发表时间' }, { k: 'journal', t: '期刊/收录机构名' }
    ],
    subFields: [
      { k: 'level', label: '论文级别', type: 'select', src: 'paperLevelReal', req: 1 },
      { k: 'title', label: '论文名称', type: 'text', req: 1, ph: '请填写论文名称' },
      { k: 'pubDate', label: '发表时间', type: 'text', req: 1, ph: '请输入发表时间' },
      { k: 'journal', label: '期刊/收录机构名', type: 'text', req: 1, ph: '请填写机构名称' },
      { k: 'issue', label: '年度及期次', type: 'text', req: 1, ph: '如：xxxx年度第xx期' },
      { k: 'authorRank', label: '作者排序', type: 'text', req: 1, ph: '请填写作者排序' },
      { k: 'indexNo', label: '论文索引号', type: 'text', num: 1, ph: '请填写阿拉伯数字' }
    ]
  },

  /* ===================== 10. 学术成果-科研 ===================== */
  {
    id: 'research', title: '学术成果-科研', req: false, kind: 'table', cols: 3,
    tips: ['科研项目成果，建议按照重要级别，从高到低，5条以内。'],
    columns: [
      { k: 'level', t: '项目级别' }, { k: 'name', t: '项目名称' },
      { k: 'range', t: '起止时间', fmt: r => (r.from || '') + (r.to ? '至' + r.to : '') },
      { k: 'org', t: '项目所属单位' }
    ],
    subFields: [
      { k: 'level', label: '项目级别', type: 'select', src: 'projLevelReal', req: 1 },
      { k: 'name', label: '项目名称', type: 'text', req: 1, ph: '请填写项目名称' },
      { k: 'from', label: '开始时间', type: 'date', req: 1, ph: '请输入开始时间' },
      { k: 'to', label: '结束时间', type: 'date', req: 1, ph: '请输入结束时间' },
      { k: 'org', label: '项目所属单位', type: 'text', req: 1, ph: '请填写项目所属单位' },
      { k: 'projNo', label: '项目编号', type: 'text', num: 1, ph: '请填写项目编号' },
      { k: 'detail', label: '具体工作要点', type: 'textarea', full: true, max: 100,
        ph: '请输入其他需要说明的信息，最多100个字符' }
    ]
  },

  /* ===================== 11. 获奖情况 ===================== */
  {
    id: 'award', title: '获奖情况', req: false, kind: 'table', cols: 3,
    tips: ['请填写获得奖学金及评优情况。'],
    columns: [
      { k: 'name', t: '获奖名称' }, { k: 'level', t: '获奖级别' },
      { k: 'date', t: '获奖时间' }, { k: 'org', t: '发证单位' }
    ],
    subFields: [
      { k: 'name', label: '获奖名称', type: 'text', req: 1, ph: '请填写获奖名称' },
      { k: 'level', label: '获奖级别', type: 'select', src: 'awardLevel', req: 1 },
      { k: 'date', label: '获奖时间', type: 'date', req: 1, ph: '请输入获奖时间' },
      { k: 'org', label: '发证单位', type: 'text', req: 1, max: 20, ph: '发证机构名称在20字以内' },
      { k: 'certNo', label: '证书编号', type: 'text', num: 1, ph: '请填写证书编号' },
      { k: 'certFile', label: '上传证书', type: 'file', full: true, limit: 1024,
        accept: '.pdf,.doc,.xls,.jpg,.png,.docx,.xlsx' },
      { k: 'remark', label: '其他备注', type: 'textarea', full: true, max: 50,
        ph: '请输入其他需要说明的信息。最多50个字符' }
    ]
  },

  /* ===================== 12. 上传电子附件 ===================== */
  {
    id: 'attachment', title: '上传电子附件', req: false, kind: 'table', cols: 2,
    tips: [
      '请上传"就业推荐表、成绩单、资格证书"等材料的扫描件，以供招聘单位了解您更多的信息。',
      '文件类型为（pdf、doc、xls、jpg、png、docx、xlsx）其中之一，大小在1024kb以内。'
    ],
    columns: [
      { k: 'type', t: '附件类型' }, { k: 'file', t: '文件名' }, { k: 'size', t: '大小' }
    ],
    subFields: [
      { k: 'type', label: '附件类型', type: 'select', src: 'attachTypeReal', req: 1 },
      { k: 'file', label: '上传附件', type: 'file', req: 1, limit: 1024,
        accept: '.pdf,.doc,.xls,.jpg,.png,.docx,.xlsx' }
    ]
  }
];

/* 其他情况说明（独立文本模块） */
window.OTHER_SECTION = {
  id: 'other', title: '其他情况说明', req: false,
  p: 'other', max: 200,
  tip: '如果有其他未说明示意，请填写在下方的输入框中。'
};

/* 求职意向可选标签 */
window.INTENTION_TAGS = [
  '国家电网', '南方电网', '省电力公司', '市供电公司', '县供电公司',
  '电力调度', '变电运维', '输电运检', '配电运检', '电力营销',
  '电气工程', '自动化', '信息技术', '新能源', '电力设计院',
  '电力科研', '发电集团', '电力施工', '海外项目', '不限'
];

/* 学历等级映射（用于"从高往低"校验） */
window.EDU_RANK = {
  '博士研究生毕业': 5,
  '硕士研究生毕业': 4,
  '大学本科毕业': 3,
  '大学专科毕业': 2
};
