from pathlib import Path

from phi.workspace.settings import WorkspaceSettings

#
# -*- Define workspace settings using a WorkspaceSettings object
# these values can also be set using environment variables or a .env file
#
ws_settings = WorkspaceSettings(
    # Workspace name: used for naming cloud resources
    ws_name="streamlit-app",
    # Path to the workspace root
    ws_root=Path(__file__).parent.parent.resolve(),
    # -*- Dev settings
    dev_env="dev",
    # -*- Dev Apps
    dev_app_enabled=True,
    dev_db_enabled=True,
    dev_jupyter_enabled=True,
    # -*- Production settings
    prd_env="prd",
    # -*- Production Apps
    prd_app_enabled=True,
    prd_db_enabled=True,
    # -*- AWS settings
    # Region for AWS resources
    aws_region="us-west-2",
    # Availability Zones for AWS resources
    aws_az1="us-west-2a",
    aws_az2="us-west-2b",
    # Subnet IDs in the aws_region
    subnet_ids=["subnet-016401b9d1d030c40", "subnet-0308f8e6192a18f70"],
    # -*- Image Settings
    # Name of the image
    image_name="streamlit-app",
    # Repository for the image
    image_repo="654654240011.dkr.ecr.us-west-2.amazonaws.com",
    # Build images locally
    build_images=True,
)
