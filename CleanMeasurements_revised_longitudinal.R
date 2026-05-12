library(readxl)
library(dplyr)
library(tidyr)
library(writexl)

# 读取数据
file_path <- "E:/HippoAnalysis/Measures2_AV1451_PET_ABETA_MRI.xlsx"
df <- read_excel(file_path)

# 需要排除的非特征列
exclude_cols <- c("Subject ID", "Scan ID", "Side", "Group")

# --- 重命名特征列（基于列位置顺序，不依赖原始列名内容）---
# 总特征列数应为 549 (Inf) + 549 (Sup) + 64 (CrestLength) = 1162
all_cols <- colnames(df)
is_feature <- !all_cols %in% exclude_cols   # 标记特征列
feature_pos <- which(is_feature)            # 特征列在 df 中的位置索引（按原始顺序）

# 第 1~549 列：保持为 combined_label InfThickness 1~549（无需修改）
# 第 550~1098 列（共549列）：重命名为 combined_label SupThickness 1~549
if (length(feature_pos) >= 1098) {
  sup_pos <- feature_pos[550:1098]
  colnames(df)[sup_pos] <- paste0("combined_label SupThickness ", 1:549)
}

# 第 1099~1162 列（共64列）：重命名为 CrestLength 1~64
if (length(feature_pos) >= 1162) {
  crest_pos <- feature_pos[1099:1162]
  colnames(df)[crest_pos] <- paste0("CrestLength ", 1:64)
}

# 此时，df 中所有特征列的列名已修正：
# - 前549列: combined_label InfThickness 1~549
# - 接着549列: combined_label SupThickness 1~549
# - 最后64列: CrestLength 1~64
# ========== 输出更正后的原始表格 ==========
output_file <- "E:/HippoAnalysis/Measures2_AV1451_PET_ABETA_MRI_corrected.csv"
write.csv(df, output_file, row.names = FALSE)
cat("已保存修正后的表格至：", output_file, "\n")

# 提取所有特征列（包括 "combined_label"）
all_feature_cols <- setdiff(colnames(df), exclude_cols)

# 仅用于 0 值转换的特征列（不含 "combined_label"）
zero_replace_cols <- all_feature_cols[!grepl("combined_label", all_feature_cols, ignore.case = TRUE)]

# 统计 0 值和异常值的数量
zero_counts <- data.frame(Feature = character(0), Zero_Count = integer(0))
outlier_counts <- data.frame(Feature = character(0), Outlier_Count = integer(0))

# ========================== 第一步：智能转换 0 值为 NA ==========================

# 按照Subject ID, Side和Scan ID排序，确保按时间顺序处理
df <- df %>%
  mutate(Scan_num = as.numeric(gsub("Scan", "", `Scan ID`))) %>%
  arrange(`Subject ID`, Side, Scan_num)

# 定义处理函数：根据历史扫描值智能处理0值
process_zero_with_history <- function(values) {
  n <- length(values)
  result <- values
  
  if (n == 1) {
    # 只有一个扫描：如果为0则转NA
    if (values[1] == 0) {
      result[1] <- NA_real_
    }
    return(result)
  }
  
  # 处理基线扫描（第一个扫描）
  if (values[1] == 0) {
    result[1] <- NA_real_
  }
  
  # 处理后续扫描
  for (i in 2:n) {
    if (values[i] == 0) {
      # 查找前一个非0且非NA的值
      j <- i - 1
      found_non_zero <- FALSE
      
      while (j >= 1) {
        if (!is.na(result[j]) && result[j] != 0) {
          found_non_zero <- TRUE
          break
        }
        j <- j - 1
      }
      
      # 如果没有找到前一个非0值，将当前0转为NA
      if (!found_non_zero) {
        result[i] <- NA_real_
      }
      # 如果找到了前一个非0值，保留当前0（不做任何操作）
    }
  }
  
  return(result)
}

# 为每个特征列处理0值（仅处理非combined_label特征）
for (feature in zero_replace_cols) {
  # 按Subject ID和Side分组处理
  df <- df %>%
    group_by(`Subject ID`, Side) %>%
    mutate(
      # 获取当前分组内该特征的值
      feature_values = as.numeric(.data[[feature]]),
      # 应用处理函数
      processed = process_zero_with_history(feature_values),
      # 更新原特征列
      !!feature := processed
    ) %>%
    ungroup() %>%
    select(-feature_values, -processed)
  
  # 统计保留的0值数量（未被转换为NA的0值）
  retained_zeros <- sum(df[[feature]] == 0, na.rm = TRUE)
  zero_counts <- rbind(zero_counts, data.frame(Feature = feature, Zero_Count = retained_zeros))
}

# ========================== 第二步：异常值处理 ==========================

# 异常值处理（遍历所有特征列，包括 "combined_label"）
for (feature in all_feature_cols) {
  values <- as.numeric(df[[feature]])  # 确保数值类型
  outlier_mask <- rep(FALSE, length(values))  # 初始化
  
  if (grepl("Thickness", feature, ignore.case = TRUE)) {
    outlier_mask <- values > 13
  } else if (grepl("Width", feature, ignore.case = TRUE)) {
    if (grepl("LatWidth|VenWidth", feature, ignore.case = TRUE)) {
      outlier_mask <- values > 60
    } else {
      outlier_mask <- values > 95
    }
  } else if (grepl("Length", feature, ignore.case = TRUE)) {
    if (grepl("PostLength|AntLength", feature, ignore.case = TRUE)) {
      outlier_mask <- values > 80
    } else {
      outlier_mask <- values > 80
    }
  }
  
  df[[feature]][outlier_mask] <- NA
  outlier_counts <- rbind(outlier_counts, data.frame(Feature = feature, Outlier_Count = sum(outlier_mask, na.rm = TRUE)))
}

# 移除辅助列
df <- df %>% select(-Scan_num)

# 保存处理后的数据
output_path <- "E:/HippoAnalysis/Measures2_AV1451_PET_ABETA_MRI_Cleaned_Mid_Long.xlsx"
write_xlsx(df, output_path)

print(paste("处理后的数据已保存至:", output_path))

# ========================== 第三步：重组 Combined Label 特征 ==========================

# 读取 HippoLabelIndex.csv
label_index_path <- "E:/HippoAnalysis/template_repair/template_repair/HippoLabelIndex.csv"
label_index <- read.csv(label_index_path)

# 提取 Var1 和不同的 Index 列
mapping_table <- label_index %>%
  mutate(FeatureName = case_when(
    Var1 <= 549  ~ paste0("combined_label InfThickness ", Var1),
    Var1 > 549   ~ paste0("combined_label SupThickness ", Var1 - 549)
  ))

# 分组生成特征列表的函数
create_grouped_feature <- function(index_column) {
  # 1. 按指定的索引列分组，计算中位数
  grouped_features <- mapping_table %>%
    group_by(.data[[index_column]]) %>%
    summarise(Features = list(FeatureName))
  
  # 存储新特征
  new_features <- data.frame(matrix(nrow = nrow(df), ncol = length(unique(mapping_table[[index_column]]))))
  colnames(new_features) <- paste0(index_column, ".", unique(mapping_table[[index_column]]))
  
  # 计算分组中位数
  for (group in unique(mapping_table[[index_column]])) {
    feature_names <- unlist(grouped_features$Features[grouped_features[[index_column]] == group])
    
    # 只选择 df 中实际存在的列，避免不存在的列报错
    valid_features <- feature_names[feature_names %in% colnames(df)]
    
    if (length(valid_features) > 0) {
      new_features[[paste0(index_column, ".", group)]] <- apply(df[, valid_features], 1, median, na.rm = TRUE)
    }
  }
  
  return(new_features)
}

# 为每个索引列生成新特征
new_features_lamella <- create_grouped_feature("AllHippoLamellaIndex")
new_features_supinf <- create_grouped_feature("AllHippoSupInfIndex")
new_features_latven <- create_grouped_feature("AllHippoLatVenIndex")
new_features_atlas <- create_grouped_feature("AllHippoAtlasIndex")
new_features_hbt <- create_grouped_feature("AllHippoHBTIndex")
new_features_lamella_atlas <- create_grouped_feature("AllHippoLamellaAtlasIndex")
new_features_hbt_atlas <- create_grouped_feature("AllHippoHBTAtlasIndex")
new_features_lamella_supinf_latven <- create_grouped_feature("AllHippoLamellaSupInfLatVenIndex")
new_features_hbt_supinf_latven <- create_grouped_feature("AllHippoHBTSupInfLatVenIndex")

# 合并新特征到原数据
df <- cbind(df, new_features_lamella, new_features_supinf, new_features_latven, new_features_atlas, new_features_hbt, 
            new_features_lamella_atlas, new_features_hbt_atlas, new_features_lamella_supinf_latven, new_features_hbt_supinf_latven)

# ========================== 第四步：重组亚区厚度特征 ==========================

# 读取 HippoSubfieldIndex.csv
subfield_index_path <- "E:/HippoAnalysis/template_repair/template_repair/HippoSubfieldIndex.csv"
subfield_index <- read.csv(subfield_index_path)

# 获取亚区和标签的映射，使用 pivot_longer 代替 gather
subfield_labels <- subfield_index %>%
  pivot_longer(cols = -Var1, names_to = "Subfield", values_to = "Label") %>%
  filter(!is.na(Label))

# 根据亚区名称和 Var1 生成新的特征
create_grouped_feature_with_labels <- function(subfield_name) {
  # 获取该亚区的标签数据
  subfield_data <- subfield_labels %>%
    filter(Subfield == subfield_name)
  
  # 提前创建一个空数据框，存储新特征
  unique_labels <- unique(subfield_data$Label)
  new_features <- data.frame(matrix(nrow = nrow(df), ncol = length(unique_labels)))
  colnames(new_features) <- paste0(subfield_name, ".", unique_labels)
  
  # 获取 df 中与该亚区相关的所有特征
  feature_names <- grep(subfield_name, colnames(df), value = TRUE)
  
  # 遍历所有唯一的 label
  for (label in unique_labels) {
    # 选出匹配当前 label 的特征列
    valid_features_for_label <- feature_names[
      sapply(feature_names, function(f) {
        # 提取特征名中的编号
        feature_number <- as.numeric(gsub(".*?(\\d+)$", "\\1", f))
        # 检查该编号是否在 subfield_data 的 Var1 里，并且对应的 Label 是否匹配
        feature_number %in% subfield_data$Var1[subfield_data$Label == label]
      })
    ]
    
    if (length(valid_features_for_label) > 0) {
      new_features[[paste0(subfield_name, ".", label)]] <- apply(df[, valid_features_for_label, drop = FALSE], 1, median, na.rm = TRUE)
    }
  }
  
  return(new_features)
}

# 为每个亚区生成新的特征列
new_features_ca1 <- create_grouped_feature_with_labels("CA1")
new_features_ca3 <- create_grouped_feature_with_labels("CA3")
new_features_ca4 <- create_grouped_feature_with_labels("CA4")
new_features_gcdg <- create_grouped_feature_with_labels("GC_DG")
new_features_hata <- create_grouped_feature_with_labels("HATA")
new_features_mole_layer <- create_grouped_feature_with_labels("mole_layer")
new_features_para_sub <- create_grouped_feature_with_labels("para_sub")
new_features_pre_sub <- create_grouped_feature_with_labels("pre_sub")
new_features_sub <- create_grouped_feature_with_labels("sub")
new_features_tail <- create_grouped_feature_with_labels("tail")

# 合并新特征到原数据
df <- cbind(df, new_features_ca1, new_features_ca3, new_features_ca4, new_features_gcdg, new_features_hata, 
            new_features_mole_layer, new_features_para_sub, new_features_pre_sub, new_features_sub, new_features_tail)

# ========================== 第五步：输出最终数据 ==========================

# 1. 识别非特征列
df_non_features <- df[, exclude_cols]

# 2. 识别新的特征列（重组后的特征）
df_new_features <- df[, !colnames(df) %in% all_feature_cols]

# 3. 识别所有 Width 和 Length 相关的原始特征
width_length_features <- grep("Width|Length", colnames(df), value = TRUE)

# 4. 只去掉 thickness 相关特征，保留 Width 和 Length
df_width_length <- df[, width_length_features]

# 5. 合并非特征列 + Width 和 Length 特征 + 新特征列
final_df <- cbind(df_non_features, df_width_length, df_new_features)

# 保存最终数据
output_path_final <- "E:/HippoAnalysis/Measures2_AV1451_PET_ABETA_MRI_Final_Regroup_Mid_Long.xlsx"
write_xlsx(final_df, output_path_final)

print(paste("最终数据已保存至:", output_path_final))

# ========================== 第六步：输出统计信息 ==========================

# 输出0值处理统计
if (nrow(zero_counts) > 0) {
  print("0值处理统计：")
  print(zero_counts)
}

# 输出异常值处理统计
if (nrow(outlier_counts) > 0) {
  print("异常值处理统计：")
  print(outlier_counts)
}

print("数据处理完成！")
