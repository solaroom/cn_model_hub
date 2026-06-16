/**
 * Helper utilities for repository metadata display
 */

/**
 * Language ISO 639-1 code to full name mapping
 * @param {string} code - ISO 639-1 language code
 * @returns {string} Full language name
 */
export function getLanguageName(code) {
  const languageMap = {
    en: "英语",
    zh: "中文",
    ja: "日语",
    ko: "韩语",
    es: "西班牙语",
    fr: "法语",
    de: "德语",
    it: "意大利语",
    pt: "葡萄牙语",
    ru: "俄语",
    ar: "阿拉伯语",
    hi: "印地语",
    nl: "荷兰语",
    pl: "波兰语",
    tr: "土耳其语",
    vi: "越南语",
    th: "泰语",
    id: "印尼语",
    he: "希伯来语",
    sv: "瑞典语",
    fi: "芬兰语",
    da: "丹麦语",
    no: "挪威语",
    cs: "捷克语",
    ro: "罗马尼亚语",
    uk: "乌克兰语",
    el: "希腊语",
    hu: "匈牙利语",
    sk: "斯洛伐克语",
    bg: "保加利亚语",
    hr: "克罗地亚语",
    sr: "塞尔维亚语",
    ca: "加泰罗尼亚语",
    multilingual: "多语言",
    code: "代码",
  };
  return languageMap[code] || code.toUpperCase();
}

/**
 * Get standard license documentation link
 * @param {string} license - License identifier
 * @returns {string|null} License documentation URL
 */
export function getStandardLicenseLink(license) {
  if (!license) return null;

  const licenseLinks = {
    mit: "https://opensource.org/licenses/MIT",
    "apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0",
    "gpl-3.0": "https://www.gnu.org/licenses/gpl-3.0.html",
    "gpl-2.0": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
    "lgpl-3.0": "https://www.gnu.org/licenses/lgpl-3.0.html",
    "bsd-3-clause": "https://opensource.org/licenses/BSD-3-Clause",
    "bsd-2-clause": "https://opensource.org/licenses/BSD-2-Clause",
    "mpl-2.0": "https://www.mozilla.org/en-US/MPL/2.0/",
    "cc0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc-by-nc-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "cc-by-nc-sa-4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    unlicense: "https://unlicense.org/",
    isc: "https://opensource.org/licenses/ISC",
    "artistic-2.0": "https://opensource.org/licenses/Artistic-2.0",
    "epl-2.0": "https://www.eclipse.org/legal/epl-2.0/",
  };

  return licenseLinks[license.toLowerCase()] || null;
}

/**
 * Format metadata key from snake_case to Title Case
 * @param {string} key - Metadata key in snake_case
 * @returns {string} Formatted key
 */
export function formatMetadataKey(key) {
  const keyNames = {
    pretty_name: "显示名称",
    license: "许可证",
    language: "语言",
    library_name: "框架",
    pipeline_tag: "任务类型",
    base_model: "基座模型",
    datasets: "训练数据集",
    task_categories: "任务",
    size_categories: "数据规模",
    multilinguality: "语言类型",
    annotations_creators: "标注来源",
    source_datasets: "来源数据集",
    configs: "配置",
    data_files: "数据文件",
    features: "字段结构",
    tags: "标签",
  };
  return keyNames[key] || key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

/**
 * Get friendly name for license
 * @param {string} license - License identifier
 * @returns {string} Friendly license name
 */
export function getLicenseName(license) {
  const licenseNames = {
    mit: "MIT 许可证",
    "apache-2.0": "Apache 2.0 许可证",
    "gpl-3.0": "GNU GPL v3.0",
    "gpl-2.0": "GNU GPL v2.0",
    "lgpl-3.0": "GNU LGPL v3.0",
    "bsd-3-clause": "BSD 3-Clause",
    "bsd-2-clause": "BSD 2-Clause",
    "mpl-2.0": "Mozilla Public License 2.0",
    "cc0-1.0": "CC0 1.0 Universal",
    "cc-by-4.0": "CC BY 4.0",
    "cc-by-sa-4.0": "CC BY-SA 4.0",
    "cc-by-nc-4.0": "CC BY-NC 4.0",
    "cc-by-nc-sa-4.0": "CC BY-NC-SA 4.0",
    unlicense: "The Unlicense",
    isc: "ISC License",
    other: "其他许可证",
  };
  return licenseNames[license.toLowerCase()] || license.toUpperCase();
}

/**
 * Get friendly name for pipeline tag
 * @param {string} tag - Pipeline tag
 * @returns {string} Friendly pipeline name
 */
export function getPipelineTagName(tag) {
  const pipelineNames = {
    "text-classification": "文本分类",
    "token-classification": "Token 分类",
    "text-generation": "文本生成",
    "text2text-generation": "文本到文本生成",
    "fill-mask": "掩码填充",
    "question-answering": "问答",
    "multiple-choice": "单项选择",
    translation: "Translation",
    summarization: "摘要",
    conversational: "对话",
    "feature-extraction": "特征提取",
    "sentence-similarity": "句子相似度",
    "zero-shot-classification": "零样本分类",
    "image-classification": "图像分类",
    "object-detection": "目标检测",
    "image-segmentation": "图像分割",
    "image-to-text": "Image-to-Text",
    "text-to-image": "Text-to-Image",
    "image-to-image": "Image-to-Image",
    "audio-classification": "Audio Classification",
    "automatic-speech-recognition": "Speech Recognition",
    "text-to-speech": "Text-to-Speech",
    "audio-to-audio": "Audio-to-Audio",
    "video-classification": "Video Classification",
    "reinforcement-learning": "Reinforcement Learning",
    "tabular-classification": "Tabular Classification",
    "tabular-regression": "Tabular Regression",
  };
  return pipelineNames[tag] || formatMetadataKey(tag);
}

/**
 * Get friendly name for task category
 * @param {string} task - Task category
 * @returns {string} Friendly task name
 */
export function getTaskCategoryName(task) {
  return getPipelineTagName(task);
}

/**
 * Format size category
 * @param {string} size - Size category (e.g., "1K<n<10K")
 * @returns {string} Formatted size
 */
export function formatSizeCategory(size) {
  return size.replace(/n/g, "N").replace(/</g, " < ").replace(/>/g, " > ");
}
