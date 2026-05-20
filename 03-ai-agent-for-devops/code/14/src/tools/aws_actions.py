"""
AWS Action Tools - RDS Database Management
Real-world actions for managing AWS RDS instances with boto3.
Uses placeholder mode when AWS is not configured.
"""
import os
from langchain_core.tools import tool


def _is_aws_configured() -> bool:
    """Check if AWS credentials are available"""
    return bool(
        os.getenv('AWS_ACCESS_KEY_ID') or 
        os.getenv('AWS_PROFILE') or
        os.getenv('AWS_ROLE_ARN')
    )


@tool
def reboot_rds_instance(db_instance_id: str, reason: str = "") -> str:
    """
    Reboot an AWS RDS database instance to reset connections and restore service.
    IMPORTANT: Always ask for user approval before using this tool. This will cause
    a brief service interruption (typically 1-3 minutes for a reboot).

    Use this when logs show "Too many connections" errors across multiple application pods,
    indicating the RDS instance has exhausted its connection limit.
    
    Args:
        db_instance_id: The RDS instance identifier (e.g., 'orders-db-prod')
        reason: Reason for the reboot (e.g., 'Connection pool exhaustion recovery')
    
    Returns:
        str: Success or error message with reboot status
    """
    if _is_aws_configured():
        return _reboot_rds_real(db_instance_id, reason)
    else:
        return _reboot_rds_placeholder(db_instance_id, reason)


def _reboot_rds_real(db_instance_id: str, reason: str) -> str:
    """Real AWS RDS reboot using boto3"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        region = os.getenv('AWS_REGION', 'us-east-1')
        rds_client = boto3.client('rds', region_name=region)
        
        # Check instance status before rebooting
        try:
            response = rds_client.describe_db_instances(
                DBInstanceIdentifier=db_instance_id
            )
            instance = response['DBInstances'][0]
            status = instance['DBInstanceStatus']
            
            if status != 'available':
                return (
                    f"Cannot reboot RDS instance '{db_instance_id}'. "
                    f"Current status: {status}. Instance must be 'available' to reboot."
                )
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBInstanceNotFoundFault':
                return f"RDS instance '{db_instance_id}' not found in region {region}."
            raise
        
        # Perform the reboot
        rds_client.reboot_db_instance(
            DBInstanceIdentifier=db_instance_id
        )
        
        return (
            f"Successfully initiated reboot of RDS instance '{db_instance_id}' "
            f"in region {region}.\n"
            f"Reason: {reason}\n"
            f"Previous status: {status}\n"
            f"Expected downtime: 1-3 minutes for a standard reboot.\n"
            f"The instance will transition: available → rebooting → available.\n"
            f"All existing connections will be dropped and new connections can be established after reboot."
        )
        
    except ImportError:
        return (
            "boto3 is not installed. Install it with: pip install boto3\n"
            "Falling back to placeholder mode."
        )
    except ClientError as e:
        return f"AWS API error: {e.response['Error']['Message']}"
    except Exception as e:
        return f"Error rebooting RDS instance: {str(e)}"


def _reboot_rds_placeholder(db_instance_id: str, reason: str) -> str:
    """Placeholder RDS reboot for learning/testing"""
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    print(f"\n{'='*70}")
    print(f"PLACEHOLDER: Would reboot AWS RDS instance")
    print(f"{'='*70}")
    print(f"Instance ID:      {db_instance_id}")
    print(f"Region:           {region}")
    print(f"Reason:           {reason}")
    print(f"AWS CLI command:  aws rds reboot-db-instance --db-instance-identifier {db_instance_id}")
    print(f"Expected:         Instance reboots in 1-3 minutes, all connections reset")
    print(f"{'='*70}\n")
    
    return (
        f"[SIMULATED] Successfully initiated reboot of RDS instance '{db_instance_id}' "
        f"in region {region}.\n"
        f"Reason: {reason}\n"
        f"Expected downtime: 1-3 minutes.\n"
        f"All existing database connections will be dropped. "
        f"Application pods will reconnect automatically via HikariCP connection pool."
    )
