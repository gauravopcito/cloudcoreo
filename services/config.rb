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
  cidr "${VPC_OCTETS}/16"
end

coreo_aws_vpc_routetable "${PRIVATE_ROUTE_NAME}" do
  action :find
  vpc "${VPC_NAME}"
end

coreo_aws_vpc_subnet "${PRIVATE_SUBNET_NAME}" do
  action :find
  route_table "${PRIVATE_ROUTE_NAME}"
  vpc "${VPC_NAME}"
end

coreo_aws_ec2_securityGroups "${MONGO_SG_NAME}" do
  action :sustain
  description "MongoDB security group"
  vpc "${VPC_NAME}"
  allows [ 
          { 
            :direction => :ingress,
            :protocol => :tcp,
            :ports => ["27017..27030"],
            :cidrs => ${MONGO_INGRESS_CIDRS}
          },{ 
            :direction => :ingress,
            :protocol => :tcp,
            :ports => [22, 28017],
            :cidrs => ${MONGO_INGRESS_CIDRS}
          },{ 
            :direction => :egress,
            :protocol => :tcp,
            :ports => ["0..65535"],
            :cidrs => ${MONGO_EGRESS_CIDRS}
          },{ 
            :direction => :egress,
            :protocol => :udp,
            :ports => ["0..65535"],
            :cidrs => ${MONGO_EGRESS_CIDRS}
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

coreo_aws_iam_instance_profile "${MONGO_NAME}" do
  action :sustain
  policies ["${MONGO_NAME}-backup"]
end

coreo_aws_ec2_instance "${MONGO_NAME}" do
  action :define
  image_id "${MONGO_AMI}"
  size "${MONGO_SIZE}"
  security_groups ["${MONGO_SG_NAME}"]
  associate_public_ip false
  role "${MONGO_NAME}"
  ssh_key "${MONGO_KEY}"
  upgrade_trigger "2"
  environment_variables [
                         "PRIVATE_IP_ADDRESS=STACK::coreo_aws_ec2_autoscaling.${MONGO_NAME}.private_ip_addresses",
			 "PUBLIC_IP_ADDRESS=STACK::coreo_aws_ec2_autoscaling.${MONGO_NAME}.public_ip_addresses",
                         "INSTANCE_IDS=STACK::coreo_aws_ec2_autoscaling.${MONGO_NAME}.instance_ids",
                        ]
end

coreo_aws_ec2_autoscaling "${MONGO_NAME}" do
  action :sustain 
  minimum ${MONGO_GROUP_SIZE_MIN}
  maximum ${MONGO_GROUP_SIZE_MAX}
  server_definition "${MONGO_NAME}"
  subnet "${PRIVATE_SUBNET_NAME}"
  upgrade({
            :upgrade_on => "dirty",
            :cooldown => 10,
            :replace => 'in-place'
          })
end

coreo_aws_route53_record "${MONGO_NAME}.db" do
  action :sustain
  type "A"
  zone "${DNS_ZONE}"
  values ["STACK::coreo_aws_ec2_autoscaling.${MONGO_NAME}.private_ip_addresses"]
end

