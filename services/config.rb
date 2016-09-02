## This file was auto-generated by CloudCoreo CLI
## This file was automatically generated using the CloudCoreo CLI
##
## This config.rb file exists to create and maintain services not related to compute.
## for example, a VPC might be maintained using:
##
## coreo_aws_vpc_vpc "my-vpc" do
##   action :sustain
##   cidr "12.0.0.0/16"
##   internet_gateway true
## end
##

coreo_aws_vpc_vpc "${VPC_NAME}" do
  action :find
  cidr "${VPC_CIDR}"
  tags ${VPC_SEARCH_TAGS}
end

coreo_aws_vpc_routetable "${PRIVATE_ROUTE_NAME}" do
  action :find
  vpc "${VPC_NAME}"
  tags ${PRIVATE_ROUTE_SEARCH_TAGS}
end

coreo_aws_vpc_subnet "${PRIVATE_SUBNET_NAME}" do
  action :find
  route_table "${PRIVATE_ROUTE_NAME}"
  vpc "${VPC_NAME}"
  tags ${PRIVATE_SUBNET_SEARCH_TAGS}
end

coreo_aws_ec2_securityGroups "${CLUSTER_NAME}-elb" do
  action :sustain
  description "load balance the ui and client connectinos"
  vpc "${VPC_NAME}"
  allows [ 
          { 
            :direction => :ingress,
            :protocol => :tcp,
            :ports => ${CLUSTER_ELB_TRAFFIC_PORTS},
            :cidrs => ${CLUSTER_ELB_TRAFFIC_CIDRS}
          },
          { 
            :direction => :egress,
            :protocol => :tcp,
            :ports => ["0..65535"],
            :cidrs => ["0.0.0.0/0"]
          }
    ]
end

coreo_aws_ec2_elb "${CLUSTER_NAME}-elb" do
  action :sustain
  type "internal"
  vpc "${VPC_NAME}"
  subnet "${PRIVATE_SUBNET_NAME}"
  security_groups ["${CLUSTER_NAME}-elb"]
  listeners ${ELB_LISTENERS}
  health_check_protocol 'tcp'
  health_check_port "${CLUSTER_TCP_HEALTH_CHECK_PORT}"
  health_check_timeout 5
  health_check_interval 120
  health_check_unhealthy_threshold 5
  health_check_healthy_threshold 2
end

coreo_aws_route53_record "${CLUSTER_NAME}" do
  action :sustain
  type "CNAME"
  zone "${DNS_ZONE}"
  values ["STACK::coreo_aws_ec2_elb.${CLUSTER_NAME}-elb.dns_name"]
end

coreo_aws_ec2_securityGroups "${CLUSTER_NAME}" do
  action :sustain
  description "cluster instances security group"
  vpc "${VPC_NAME}"
  allows [
          { 
            :direction => :ingress,
            :protocol => :tcp,
            :ports => ${CLUSTER_INSTANCE_TRAFFIC_PORTS},
            :cidrs => ${CLUSTER_INSTANCE_TRAFFIC_CIDRS}
          },
          { 
            :direction => :ingress,
            :protocol => :udp,
            :ports => ${CLUSTER_INSTANCE_TRAFFIC_PORTS},
            :cidrs => ${CLUSTER_INSTANCE_TRAFFIC_CIDRS}
          },
          { 
            :direction => :ingress,
            :protocol => :tcp,
            :ports => ${CLUSTER_INSTANCE_TRAFFIC_PORTS},
            :groups => ["${CLUSTER_NAME}-elb"]
          },
          { 
            :direction => :egress,
            :protocol => :udp,
            :ports => ['0..65535'],
            :cidrs => ['0.0.0.0/0']
          },
          { 
            :direction => :egress,
            :protocol => :tcp,
            :ports => ['0..65535'],
            :cidrs => ['0.0.0.0/0']
          }
    ]
end

coreo_aws_s3_policy "${BACKUP_BUCKET}-policy" do
  action :sustain
  policy_document <<-EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${BACKUP_BUCKET}/*",
        "arn:aws:s3:::${BACKUP_BUCKET}"
      ]
    }
  ]
}
EOF
end

coreo_aws_s3_bucket "${BACKUP_BUCKET}" do
   action :sustain
   bucket_policies ["${BACKUP_BUCKET}-policy"]
   region "${BACKUP_BUCKET_REGION}"
end

coreo_aws_iam_policy "${MONGO_NAME}-backup" do
  action :sustain
  policy_name "Allow${MONGO_NAME}S3Backup"
  policy_document <<-EOH
{
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
          "arn:aws:s3:::${BACKUP_BUCKET}/${REGION}/mongo/${ENV}/${MONGO_NAME}",
          "arn:aws:s3:::${BACKUP_BUCKET}/${REGION}/mongo/${ENV}/${MONGO_NAME}/*"
      ],
      "Action": [ 
          "s3:*"
      ]
    },
    {
      "Effect": "Allow",
      "Resource": "arn:aws:s3:::*",
      "Action": [
          "s3:ListAllMyBuckets"
      ]
    },
    {
      "Effect": "Allow",
      "Resource": [
          "arn:aws:s3:::${BACKUP_BUCKET}",
          "arn:aws:s3:::${BACKUP_BUCKET}/*"
      ],
      "Action": [
          "s3:GetBucket*", 
          "s3:List*" 
      ]
    }
  ]
}
EOH
end

coreo_aws_iam_policy "${CLUSTER_NAME}" do
  action :sustain
  policy_name "${CLUSTER_NAME}ServerIAMPolicy"
  policy_document <<-EOH
{
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
          "*"
      ],
      "Action": [ 
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeInstanceAttribute",
          "ec2:DescribeInstanceStatus",
          "ec2:DescribeInstances",
          "ec2:DescribeTags"
      ]
    }
  ]
}
EOH
end

coreo_aws_iam_instance_profile "${CLUSTER_NAME}" do
  action :sustain
  policies ["${CLUSTER_NAME}"]
end

coreo_aws_ec2_instance "${CLUSTER_NAME}" do
  action :define
  image_id "${CLUSTER_AMI}"
  size "${CLUSTER_SIZE}"
  security_groups ["${CLUSTER_NAME}"]
  role "${CLUSTER_NAME}"
  ssh_key "${CLUSTER_KEY}"
end

coreo_aws_ec2_autoscaling "${CLUSTER_NAME}" do
  action :sustain 
  minimum ${CLUSTER_GROUP_SIZE_MIN}
  maximum ${CLUSTER_GROUP_SIZE_MAX}
  server_definition "${CLUSTER_NAME}"
  subnet "${PRIVATE_SUBNET_NAME}"
  elbs ["${CLUSTER_NAME}-elb"]
  health_check_grace_period ${CLUSTER_HEALTH_CHECK_GRACE_PERIOD}
  upgrade({
            :upgrade_on => "dirty",
            :cooldown => ${CLUSTER_UPGRADE_COOLDOWN}
        })
end
