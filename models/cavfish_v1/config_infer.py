# models/cavfish_v1/config_infer.py
default_scope = "mmpose"

custom_imports = dict(
    imports=[
        "mmpretrain.models",
        "custom_transforms",
        "phenolosses.phenotype_distance_loss",
        "phenolosses.vitpose_head_pheno",
    ],
    allow_failed_imports=False,
)

codec = dict(type="UDPHeatmap", input_size=(192, 256), heatmap_size=(48, 64), sigma=2)

metainfo = dict(
    dataset_name="fish_20kpt",
    keypoint_info={...},   # your 20 kps
    skeleton_info={},
    joint_weights=[1.0] * 20,
    sigmas=[0.025] * 20,
    flip_pairs=[],
    num_keypoints=20,
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
        img_size=(256, 192),
        patch_size=16,
        qkv_bias=True,
        drop_path_rate=0.3,
        with_cls_token=False,
        out_type="featmap",
        patch_cfg=dict(padding=2),
        # IMPORTANT: make this path relative to repo or ship the file too
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
            pairs=[(0,1), (3,2), (4,5), (6,7), (8,9), (10,11),
                   (12,3), (0,3), (0,13), (14,15), (14,3),
                   (0,16), (2,17), (18,19)],
            degree_normalize=True,
            scale_by_SL=True,
            beta=10.0,
        ),
        alpha_pheno=1e-2,
    ),
    test_cfg=dict(flip_test=False),
)

