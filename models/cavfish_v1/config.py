# models/cavfish_v1/config.py
default_scope = "mmpose"

custom_imports = dict(
    imports=[
        "mmpretrain.models",
        "custom_transforms",
        "phenolosses.phenotype_distance_loss",
        "phenolosses.vitpose_head_pheno",
        "mmpose.models.losses.heatmap_loss",
    ],
    allow_failed_imports=False,
)

codec = dict(
    type="UDPHeatmap",
    input_size=(192, 256),     # (W, H)
    heatmap_size=(48, 64),
    sigma=2,
)

metainfo = dict(
    dataset_name="fish_20kpt",
    paper_info={},
    keypoint_info={
        0: dict(name="kp1", id=0, color=[255, 0, 0], type="upper", swap=""),
        1: dict(name="kp2", id=1, color=[255, 0, 0], type="upper", swap=""),
        2: dict(name="kp3", id=2, color=[255, 0, 0], type="upper", swap=""),
        3: dict(name="kp4", id=3, color=[255, 0, 0], type="lower", swap=""),
        4: dict(name="kp5", id=4, color=[255, 0, 0], type="lower", swap=""),
        5: dict(name="kp6", id=5, color=[255, 0, 0], type="upper", swap=""),
        6: dict(name="kp7", id=6, color=[255, 0, 0], type="lower", swap=""),
        7: dict(name="kp8", id=7, color=[255, 0, 0], type="upper", swap=""),
        8: dict(name="kp9", id=8, color=[255, 0, 0], type="lower", swap=""),
        9: dict(name="kp10", id=9, color=[255, 0, 0], type="upper", swap=""),
        10: dict(name="kp11", id=10, color=[255, 0, 0], type="lower", swap=""),
        11: dict(name="kp12", id=11, color=[255, 0, 0], type="upper", swap=""),
        12: dict(name="kp13", id=12, color=[255, 0, 0], type="upper", swap=""),
        13: dict(name="kp14", id=13, color=[255, 0, 0], type="upper", swap=""),
        14: dict(name="kp15", id=14, color=[255, 0, 0], type="lower", swap=""),
        15: dict(name="kp16", id=15, color=[255, 0, 0], type="lower", swap=""),
        16: dict(name="kp17", id=16, color=[255, 0, 0], type="lower", swap=""),
        17: dict(name="kp18", id=17, color=[255, 0, 0], type="upper", swap=""),
        18: dict(name="kp19", id=18, color=[255, 0, 0], type="upper", swap=""),
        19: dict(name="kp20", id=19, color=[255, 0, 0], type="lower", swap=""),
    },
    skeleton_info={},
    joint_weights=[1.0] * 20,
    sigmas=[0.025] * 20,
    flip_pairs=[],
    num_keypoints=20,
    upper_body_ids=[0, 1, 2, 4, 6, 8, 10, 11, 12, 16, 17],
    lower_body_ids=[3, 13, 14, 15, 5, 18, 19, 7, 9],
)

model = dict(
    type="TopdownPoseEstimator",
    data_preprocessor=dict(
        type="PoseDataPreprocessor",
        mean=[123.675, 116.28, 103.53],
        std=[58.395, 57.12, 57.375],
        bgr_to_rgb=True,
    ),
    backbone=dict(
        type="mmpretrain.VisionTransformer",
        arch="base",
        img_size=(256, 192),   # (H, W) consistent with codec input_size (W,H)
        patch_size=16,
        qkv_bias=True,
        drop_path_rate=0.3,
        with_cls_token=False,
        out_type="featmap",
        patch_cfg=dict(padding=2),
        init_cfg=dict(
            type="Pretrained",
            checkpoint="checkpoints/mae_pretrain_vit_base_20230913.pth",
        ),
    ),
    head=dict(
        type="HeatmapHeadPheno",
        in_channels=768,
        out_channels=20,
        loss=dict(type="KeypointMSELoss", use_target_weight=True),
        deconv_out_channels=(256, 256),
        deconv_kernel_sizes=(4, 4),
        decoder=codec,
        loss_pheno=dict(
            type="PhenotypeDistanceLoss",
            pairs=[
                (0, 1), (3, 2), (4, 5), (6, 7), (8, 9), (10, 11),
                (12, 3), (0, 3), (0, 13), (14, 15), (14, 3),
                (0, 16), (2, 17), (18, 19)
            ],
            degree_normalize=True,
            scale_by_SL=True,
            beta=10.0,
        ),
        alpha_pheno=1e-2,
    ),
    test_cfg=dict(
        flip_test=False,
        flip_mode="heatmap",
        shift_heatmap=False,
    ),
)

# Optional: keep a minimal test_pipeline for future use (not required by current infer.py)
test_pipeline = [
    dict(type="LoadImageFromFile"),
    dict(type="GetBBoxCenterScale", padding=1.0),
    dict(type="TopdownAffine", input_size=codec["input_size"], use_udp=True),
    dict(type="PackPoseInputs"),
]
