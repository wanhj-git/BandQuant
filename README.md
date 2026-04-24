# 📖 Introduction

BandQuant is a Western Blot experiment data management platform developed based on the Ant Design Pro framework. It aims to provide life science researchers with comprehensive solutions for experimental data collection, processing, analysis, and visualization.

The platform supports the complete experimental workflow from sample management, image acquisition, grayscale measurement to data normalization calculations and chart generation. It also offers a guest mode for quick data analysis without registration.

## Core Features

- 🧪 **Complete Experimental Workflow**: Wizard-based design guiding you through the entire process from sample setup to result export
- 📊 **Professional Image Analysis**: Integrated multiple image processing tools for precise band grayscale measurement
- 📈 **Automated Data Calculation**: One-click completion of reference normalization and treatment control calculations
- 🎨 **Diverse Visualization**: Supports color/grayscale themes, generates publication-ready charts
- 🌍 **Internationalization**: Full Chinese and English language switching
- 👤 **Quick Guest Access**: Use band analysis features without registration

---

# ✨ Features

## Experiment Management

| Feature | Description |
|---------|-------------|
| Multi-step Wizard | 4 steps guiding complete experimental workflow |
| Batch Sample Management | Support batch adding samples and group management |
| Control Group Setting | Auto-identify and manage experimental control groups |
| Tree Directory Structure | Support multi-level directory organization of experimental data |
| Recent Editing | Quick access to recently edited experiments |

## Image Processing

| Feature | Description |
|---------|-------------|
| Multi-format Support | Support PNG, JPG, TIFF and other common image formats |
| Batch Upload | Support simultaneous upload of multiple files |
| Image Cropping | Precisely crop region of interest (ROI) |
| Background Removal | Remove background noise interference |
| Invert Colors | Support image color inversion |
| AI Auto-framing | Support AI automatic framing of calculation areas |

## Data Analysis

| Feature | Description |
|---------|-------------|
| Grayscale Measurement | Measure IntDen, Area, Mean, Min, Max values of bands |
| Reference Normalization | Normalize based on reference genes (e.g., GAPDH, β-actin) |
| Treatment Control Calculation | Calculate expression changes relative to control group |
| Multi-chart Display | Independent charts + integrated charts dual view |
| Reference Alignment | Specify reference sample, auto-calculate volume needed for other samples |

## Data Export

| Format | Description |
|--------|-------------|
| PNG | Export charts and collage images as PNG images |
| XLSX | Export data tables as XLSX files |
| TIFF | Raw image support for TIFF format |

---

# 🛠 Tech Stack

## Frontend Framework

- **Core Framework**: React 18.2.0
- **Build Tool**: UmiJS 4.1.0
- **UI Component Library**: Ant Design 5.26.7
- **Page Components**: Ant Design Pro Components 2.8.10

## Image & Charts

- **Canvas Processing**: Fabric.js 6.4.2
- **Chart Library**: ECharts 5.6.0
- **Image Export**: html2canvas
- **TIFF Parsing**: tiff.js

## Utilities

- **HTTP Client**: Axios 1.7.7
- **Date Processing**: dayjs 1.11.10
- **Drag & Drop Sorting**: @dnd-kit/core
- **Excel Processing**: xlsx 0.18.5
- **Encryption**: jsencrypt

## Development Tools

- **Type Checking**: TypeScript 4.9.5
- **Code Standards**: ESLint + Prettier
- **Unit Testing**: Jest
- **Mock Service**: MockJS

---

# 📁 Project Structure

```
Client_Codeup/
├── config/                      # Configuration directory
│   ├── config.ts               # Main configuration file
│   ├── defaultSettings.ts      # Default layout settings
│   ├── proxy.ts                # Proxy configuration
│   └── routes.ts               # Route configuration
├── mock/                       # Mock data directory
├── public/                     # Static resources
│   ├── icons/                 # Application icons
│   └── scripts/               # Script files
├── src/                        # Source code directory
│   ├── components/            # Reusable components
│   │   ├── ExpeOverview/     # Experiment overview component
│   │   ├── Footer/           # Footer component
│   │   ├── HeaderDropdown/   # Header dropdown menu
│   │   ├── ImageEditor/      # Image editor core
│   │   │   ├── CompositionEditor/    # Composition editor
│   │   │   ├── CroppingEditor/       # Cropping editor
│   │   │   ├── MeasurementEditor/    # Measurement editor
│   │   │   │   ├── ConvertToGrayscaleTool.tsx  # Grayscale conversion
│   │   │   │   ├── InvertTool.tsx              # Invert tool
│   │   │   │   ├── MeasureTool.tsx             # Measure tool
│   │   │   │   ├── RemoveBackgroundTool.tsx    # Background removal
│   │   │   │   └── MeasurementTable.tsx        # Measurement table
│   │   │   ├── EditorCanvas.tsx       # Canvas component
│   │   │   └── LogViewer.tsx          # Log viewer
│   │   └── RightContent/            # Right content area
│   ├── constants/              # Constants definition
│   │   └── chartSettings.ts    # Chart configuration constants
│   ├── layouts/                # Layout components
│   │   └── BasicLayout.tsx     # Basic layout
│   ├── locales/               # Internationalization resources
│   │   ├── en-US/             # English resources
│   │   └── zh-CN/             # Chinese resources
│   ├── models/                # Global state management
│   │   ├── CategoryExpeDataModel.ts  # Category experiment data model
│   │   ├── CategoryModel.ts          # Category model
│   │   ├── ExpeDataModel.ts          # Experiment data model
│   │   └── toolModel.ts             # Tool model
│   ├── pages/                  # Page components
│   │   ├── main/              # Main page
│   │   ├── newExperiment/     # New experiment page
│   │   │   ├── NewExpeSample/         # Sample management
│   │   │   ├── NewExpeParameter/      # Parameter settings
│   │   │   ├── NewExpeOriginalData/   # Raw data
│   │   │   ├── NewExpeDataProcess/    # Data processing
│   │   │   ├── NewExpeCalculateDataTable/  # Calculate table
│   │   │   └── NewExpeResult/         # Experiment result
│   │   ├── GuestMode/         # Guest mode
│   │   ├── SingleExpe/        # Single experiment details
│   │   └── user/              # User-related pages
│   │       ├── login/         # Login page
│   │       └── register/      # Register page
│   ├── services/              # API service layer
│   │   └── labnote/           # Lab note service
│   │       └── mainLogic.ts   # Core business logic
│   ├── types/                 # TypeScript type definitions
│   │   └── expeDataInterface.ts  # Experiment data types
│   ├── utils/                 # Utility functions
│   │   ├── exportToExcel.ts   # Excel export
│   │   └── utils.ts           # Common utilities
│   ├── app.tsx                # Application entry
│   └── global.tsx             # Global configuration
├── tests/                     # Test files
├── experimentTypes.json      # Experiment types configuration
├── package.json              # Project dependencies
└── tsconfig.json             # TypeScript configuration
```


# 📖 User Guide

## 1. User Login and Registration

### 1.1 User Registration
Visit registration page: https://www.tiaodaibao.com/user/register

#### 1.1.1 Username & Password Registration

| Field | Description | Required |
|-------|-------------|----------|
| Username | Login account | ✅ |
| Password | Account password | ✅ |
| Email | Receive verification email | ❌ |
| Phone Number | Contact information | ❌ |

#### 1.1.2 Email Registration

| Field | Description | Required |
|-------|-------------|----------|
| Email Address | Email address for registration | ✅ |
| Email Verification Code | Verification code received in email | ✅ |
| Password | Account password | ✅ |
| Confirm Password | Re-enter password | ✅ |

### 1.2 User Login

Log in using your registered username and password or email. After login, you can access full features:

- Create and manage experiments
- Upload and process images
- Export analysis results
- Directory structure management

### 1.3 Guest Mode

Click the "Quick Version Without Login" button on the login page to use all analysis features without registration. In guest mode:

- All data is stored locally in the browser
- Data will not be retained after closing the browser
- Suitable for quick verification or single analysis

## 2. Create New Experiment

### 2.1 Access

After logging in, click the "New Experiment" button in the upper left of the main page, or right-click on the left directory tree and select "New Experiment". Experiments are saved in the root directory by default.

### 2.2 Experiment Wizard Flow

The system uses a 4-step wizard design:

```
┌─────────────┐
│  Step 1     │ ← Experiment Setup (basic info + sample setup)
│  Setup      │
└──────┬──────┘
       ↓
┌─────────────┐
│  Step 2     │ ← Raw Data (upload WB images)
│  Raw Data   │
└──────┬──────┘
       ↓
┌─────────────┐
│  Step 3     │ ← Data Processing (band measurement, calculation)
│  Processing │
└──────┬──────┘
       ↓
┌─────────────┐
│  Step 4     │ ← Experiment Results (view charts, export)
│  Results    │
└─────────────┘
```


## 3. Sample Management (Step 1)

### 3.1 Add Samples

Click the "+ Add Row" button at the bottom of the table or use the batch add feature:

| Operation | Description |
|-----------|-------------|
| Single Add | Add sample information one by one |
| Batch Add | Set quantity and add multiple at once |

### 3.2 Control Group Setting

- **Important**: Each experiment must have **exactly one** control group
- The system automatically marks the first sample as the control group
- You can toggle other samples as the control group via the switch
- Cannot proceed to the next step if no control group is set or multiple control groups are set

### 3.4 Sample Grouping

Support grouping samples for easier data analysis:

- Samples in the same group are displayed together
- Group information is preserved in the experiment record
- Support cross-group comparative analysis

---

## 4. Raw Data Management (Step 2)

### 4.1 Upload Images

Click the dashed border area to upload Western Blot image files:

| Supported Formats | Description |
|-------------------|-------------|
| PNG | Portable Network Graphics |
| JPG/JPEG | Joint Photographic Experts Group |
| TIFF/TIF | Tagged Image File Format (multi-page support) |

### 4.2 Batch Upload

Support uploading multiple image files simultaneously:

1. Click the upload area
2. Hold Ctrl/Cmd to select multiple files in the file dialog
3. Click confirm to upload

### 4.3 Image Cropping

If cropping is needed after upload:

1. Click the "Crop" button in the operation column
2. Drag to select the area in the crop editor
3. Click "Confirm" to save the crop result

### 4.4 Mark Reference Genes

In the image list:

| Operation | Description |
|-----------|-------------|
| Enable Reference Switch | Mark this gene as a reference (e.g., GAPDH, β-actin) |
| Gene Name | Recognize from filename or manually edit |

**Important**: References are used for subsequent data normalization calculations, make sure to mark them correctly.

---

## 5. Data Processing (Step 3)

### 5.1 Grayscale Measurement

Click the "Process" button in the operation column to enter the measurement editor:

**Tool Panel Description:**

| Tool | Function | Use Case |
|------|----------|----------|
| Background Removal | Remove background noise | When band background is uneven |
| Invert Colors | Invert image colors | When original colors are opposite to expected |
| Measure Tool | Measure band grayscale values | Extract band signal intensity |

**Measurement Process:**

1. **Preprocess Image** (if needed)
   - Use tools like background removal, color inversion to preprocess the image

2. **Draw Measurement Rectangles**
   - Drag on the image to draw rectangle boxes
   - Each rectangle box corresponds to one sample lane
   - The number of rectangles should match the number of samples
   - You can also click "Auto-framing" button to let AI automatically identify rectangles

3. **Extract Data**
   - Click the "Calculate Values" button
   - System calculates and displays measurement results

4. **Confirm and Return**
   - Review IntDen, Area, Mean, Min, Max values
   - Click "Return" to save data

### 5.2 Data Measurement Parameters

| Parameter | Description | Unit |
|-----------|-------------|------|
| IntDen | Integrated optical density value, representing total band intensity | - |
| Area | Band coverage area | pixels |
| Mean | Band average grayscale value | - |
| Min | Band minimum grayscale value | - |
| Max | Band maximum grayscale value | - |

### 5.3 Auto Calculation

When reference processing is complete, click the "One-Click Calculate" button:

| Calculation Step | Description |
|------------------|-------------|
| Reference Normalization | sample_value / ref_gene_value |
| Treatment Control | normalized_value / control_value |

### 5.4 Data Export
- After all image processing is complete, data will be processed into three tables: "Signal Intensity", "Reference Normalized", and "Final Results".
- Click the "Export" button in the upper right corner of the table to export as xlsx format.

### 5.5 Reference Alignment
- Select a reference sample, and the system will automatically align the volumes of other samples

---

## 6. Experiment Results (Step 4)

### 6.1 Data View Switching

Support three data views:

| View | Description |
|------|-------------|
| Signal Intensity | Shows raw grayscale values of bands |
| Reference Normalized | Shows reference-normalized values |
| Final Results | Shows expression changes relative to control group |

### 6.2 Chart Theme

| Theme | Description | Applicable Scenario |
|-------|-------------|---------------------|
| Color | Use multiple colors to distinguish samples | Presentations and general reports |
| Grayscale | Use grayscale scale to distinguish samples | Publication |

### 6.3 Band Visualization

In the "Data Integration" area at the bottom of the page:

| Feature | Description |
|---------|-------------|
| Drag to Sort | Drag bands to adjust display order |
| Parameter Adjustment | Adjust font, spacing and other parameters |

**Adjustable Parameters:**

| Parameter | Description | Range |
|-----------|-------------|-------|
| Gene Font Size | Display font size of band names | 12-32px |
| Image Spacing | Spacing between band images | -30~50px |
| Sample Font Size | Display font size of sample labels | 10-24px |
| Sample Spacing | Spacing between sample labels | 20-120px |
| Label Offset | Horizontal offset of sample labels | 0-80px |

### 6.4 Export Functions

| Export Type | Operation | Format |
|-------------|-----------|--------|
| Chart Export | Click save button in the upper right corner of the chart | PNG |
| Collage Export | Click "Save Collage Image" button | PNG |

---

# 📊 Parameter Description

## Sample Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| isControl | boolean | Whether this is a control group sample | false |
| content | string | Sample name/number | empty |
| samplegroup | string | Sample group | empty |
| volume | number | Loading volume (μL) | empty |
| well | number | Well position number | auto |

## Image Processing Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| imageUrl | string | Image DataURL or URL |
| geneName | string | Corresponding gene name |
| isRef | boolean | Whether it is a reference gene |

---

# 🔌 API Interfaces

## Experiment Management

| Interface | Method | Description |
|-----------|--------|-------------|
| `/api/create_experiment` | POST | Create new experiment |
| `/api/save_experiment` | POST | Save experiment data |
| `/api/rename_experiment` | POST | Rename experiment |
| `/api/delete_experiment` | POST | Delete experiment |
| `/api/move_experiment` | POST | Move experiment |

## Directory Management

| Interface | Method | Description |
|-----------|--------|-------------|
| `/api/create_folder` | POST | Create directory |
| `/api/rename_folder` | POST | Rename directory |
| `/api/delete_folder` | POST | Delete directory |
| `/api/move_folder` | POST | Move directory |

## User Related

| Interface | Method | Description |
|-----------|--------|-------------|
| `/api/register` | POST | User registration |
| `/api/send-email-code` | POST | Send email verification code |
| `/api/save_settings` | POST | Save user settings |

## Data Query

| Interface | Method | Description |
|-----------|--------|-------------|
| `/api/category_list` | GET | Query user's directory structure and included experiments |
| `/api/experiments_list` | GET | Paginated query of all experiment data under a folder |
| `/api/one_experiment/${param0}` | GET | Query experiment data, return complete experiment data by ID |
| `/api/experiments/recent` | GET | Query 6 most recently edited experiments |

---

# ❓ FAQ

## Q1: Uploaded TIFF files cannot be displayed?

**A**: Please ensure the TIFF file format is correct. Some TIFF files generated by scanners may contain special encoding. If you encounter problems, please convert TIFF to PNG format before uploading.

## Q2: Rectangle position is inaccurate during measurement?

**A**: On the existing basis, you can select a single rectangle box to adjust its position.

## Q3: Reference normalization calculation failed?

**A**: Please confirm the following conditions:
1. Reference genes are correctly marked
2. Reference images are processed and data is extracted
3. Sample data is complete without missing values

## Q4: How to change language to Chinese?

**A**: Click the language switch button in the upper right corner of the page to switch between Chinese and English.

---

# 📄 License

This project is open source under the MIT License.

---

# 🙏 Acknowledgments

- [Ant Design Pro](https://pro.ant.design) - Enterprise-level middle platform frontend/design solution
- [UmiJS](https://umijs.org/) - Scalable enterprise-level frontend application framework
- [ECharts](https://echarts.apache.org/) - Data visualization chart library
- [Fabric.js](http://fabricjs.com/) - Flexible and powerful Canvas library
