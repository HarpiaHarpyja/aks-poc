# container-poc

POC AKS Autoscaled

## Arquivos do repositório

Os arquivos YAML são as instruções de como o Kubernetes deve rodar sua aplicação:

### Arquivo main

O arquivo main.yaml é o seu robô de automação (pipeline) rodando no GitHub. Ele é responsável por fazer o deploy das novas versões sempre que um novo push é enviado.

| Passo | Ação no main.yaml | O que Acontece | 
| :--- | :--- | :--- |
| 1. | Code checkout | O robô baixa a última versão do seu código do repositório (o que acabou de ser "pusheado" para a branch main)
| .2.-3. | Login no Azure e ACR | O robô se autentica no Azure (usando AZURE_CREDENTIALS) e no Azure Container Registry (ACR), que é o seu depósito de imagens Docker
|.4.-5. | Build e Push da Imagem | Seu código Python é transformado em uma Imagem Docker (um pacote auto-suficiente) e é enviada para o seu depósito (ACR). A tag latest garante que é a versão mais nova.
| 6. | Set AKS Context | O robô se conecta ao seu cluster AKS (clusterk8s) para saber onde implantar as coisas.
| 7. / 7a / 7b | Criação de Secrets | O robô cria (ou atualiza) objetos secretos no Kubernetes para guardar informações confidenciais, como a senha do banco de dados (DB_PASS) e a chave de serviço do GCP, sem expô-las no código.
| 8. | Deploy to AKS | O robô finalmente aplica todos os seus arquivos de configuração Kubernetes (.yaml) no cluster, implantando a nova versão da sua aplicação.

### Arquivos YAMLs

Os arquivos YAML são as instruções de como o Kubernetes deve rodar sua aplicação:

| Arquivo | Objeto Kubernetes | O que Ele Faz |
| :--- | :--- | :--- |
| hello-python.yaml | Deployment | Cria e gerencia os Pods (instâncias) da sua aplicação Python. Ele garante que a imagem do ACR seja usada, define recursos de CPU/Memória, e monta o secret do GCP como um arquivo dentro do contêiner |
| hpa-python.yaml | HorizontalPodAutoscaler (HPA) | Diz ao Kubernetes para escalar automaticamente o número de instâncias (Pods) de 1 até 5 se o uso médio de CPU passar de 50%. |
| ingress-tls.yaml | Ingress | É o ponto de entrada. Ele gerencia o tráfego externo para sua aplicação, define a regra de domínio (hello-python-aks.duckdns.org) e configura o TLS (HTTPS) usando o certificado que o Cert-Manager irá gerar. |
| cluster-issuer.yaml  | ClusterIssuer | É a instrução para o Cert-Manager de como obter um certificado (neste caso, do Let's Encrypt). |

## Como verificar logs no terminal da Azure

1. Abra um terminal da Azure.

1. Faça login no terminal. Use o az aks get-credentials para que o Azure CLI baixe o arquivo de configuração do cluster e o mescle com o seu arquivo kubeconfig local.
```
az aks get-credentials --resource-group k8scluster_group --name clusterk8s --overwrite-existing
```

2. Liste os Pods do container.
```
kubectl get pods -n azure-store-1758905293727
```

3. Identificar os IPs **público** e  **externo** do Pod

![alt text](image.png)

A distinção entre IP Externo e IP Interno é crucial para entender o fluxo de tráfego no seu cluster Azure Kubernetes Service (AKS).

| Recurso/Componente | Tipo de IP | Finalidade |
| :--- | :--- | :--- |
| **Load Balancer (`EXTERNAL-IP`)** | **IP Externo** | É o endereço público. Recebe o tráfego do usuário vindo da Internet. |
| **Service (`CLUSTER-IP`)** | **IP Interno** | É o endereço de rede interno do cluster. Roteia o tráfego do Load Balancer para um conjunto de Pods. |
| **Pods** | **IP Interno** | É o endereço de rede para o container. Onde sua aplicação está rodando e se comunicando internamente. |

Assim, o **IP Externo** atua como o **porteiro** que recebe visitantes da web, e o **IP Interno** atua como o **sistema de endereçamento** dentro da rede do cluster para que os componentes internos (Pods e Services) possam se encontrar e se comunicar com segurança.



# Comandos Importantes para Verificação do Processo de Deploy e Rede

1. 🔍 Status dos Pods e Deployment

Este comando verifica se a sua aplicação foi implantada corretamente e se as instâncias (Pods) estão em estado Running.

| Comando | Por que é importante? | 
| :--- | :---  |
| kubectl get deploy,pod -n azure-store-1758905293727 | Confirma se o Deployment (hello-python-deployment) está READY (ex: 1/1) e se os Pods estão em estado Running. |
| kubectl logs hello-python-deployment-86c54bb7c7-bfgh5 --namespace azure-store-1758905293727 | Lista os logs do Pod |
| kubectl get deployment -n azure-store-1758905293727 | Lista os Deployments |
| kubectl scale deployment/hello-python-deployment --replicas=0 -n azure-store-1758905293727 | Interrompe o Deployment |
| kubectl scale deployment/hello-python-deployment --replicas=1 -n azure-store-1758905293727 | Reinicia o Deployment |

2. 🔌 Status do Service da Aplicação

Este comando confirma que o Service interno (ClusterIP) foi criado para que o Ingress Controller possa alcançá-lo.

| Comando | Por que é importante? |
| :--- | :--- |
| kubectl get svc -n azure-store-1758905293727 | Confirma que o hello-python-service é do tipo ClusterIP e se o Service cm-acme-http-solver (do Cert-Manager) existe para o desafio HTTP-01.
| kubectl get service -n azure-store-1758905293727 hello-python-service | Para obter o IP do Service |

3. 🌐 Status do NGINX Ingress Controller (O IP Público)

Este é o comando para garantir que o seu LoadBalancer existe e está ativo, fornecendo o IP público.

| Comando | Por que é importante? |
| :--- | :--- |
| kubectl get svc -n ingress-nginx ingress-nginx-controller | Confirma o IP público (EXTERNAL-IP) do NGINX Ingress Controller. Este IP deve ser igual ao configurado no DuckDNS. |

4. 🔗 Status do Ingress (Roteamento)

Este comando verifica se o objeto Ingress foi criado corretamente e se está apontando para o Service correto (hello-python-service).

| Comando | Por que é importante? |
| :--- | :--- |
| kubectl get ingress -n azure-store-1758905293727 hello-python-ingress | Confirma se o NGINX Ingress Controller reconheceu a regra para o seu Host (hello-python-aks.duckdns.org). |

5. 🔒 Status do Certificado TLS (HTTPS)

Este é o comando para checar se o Cert-Manager conseguiu completar o desafio ACME e gerar o certificado, que é crucial para o acesso HTTPS.

| Comando | Por que é importante? |
| :--- | :--- |
| kubectl get certificate -n azure-store-1758905293727 hello-python-tls-secret | Verifica se o campo READY está como True. Se estiver False, o HTTPS não funciona (e a causa mais provável é o NSG bloqueado). |

6. 📖 Logs do NGINX Ingress Controller

Se o acesso falhar, este comando fornece os logs do NGINX, onde você pode ver erros de roteamento ou problemas de certificado.

| Comando | Por que é importante? |
| :--- | :--- |
| `kubectl logs -n ingress-nginx $(kubectl get pods -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx -o jsonpath='{.items[0].metadata.name}')tail` | Fornece os logs do NGINX |

O IP Externo do nosso App é: `http://52.255.214.130/`.

## Variáveis de configuração
I. Configuração Inicial e Variáveis
Dadas as variáveis de configuração:

```
$NOME_CLUSTER="clusterk8s" # nome do cluster do AKS
$RG_PRINCIPAL="k8scluster_group"
$NSG_RG="MC_k8scluster_group_clusterk8s_eastus"
NSG_NAME=$(az network nsg list \
    --resource-group $NSG_RG \
    --query "[?contains(name, 'aks-agentpool')].name" -o tsv) # $NSG_NAME="aks-agentpool-30022306-nsg"
SEU_EMAIL="<SEU_EMAIL_PARA_LETS_ENCRYPT>"
SEU_DOMINIO="<SEU_DOMINIO_REAL_EX_app.minhaempresa.com>"
NS_APP="azure-store-1758905293727" # Namespace da sua aplicação
$RG_NO=$(az aks show --resource-group $RG_CLUSTER --name $NOME_CLUSTER --query nodeResourceGroup -o tsv)
# Retornará algo como MC_k8scluster_group_clusterk8s_eastus
echo "RG de Infraestrutura: $RG_NO"
```

Para descobrir o nome de algumas variáveis:
```
# Nome do NSG
az network nsg list --resource-group MC_k8scluster_group_clusterk8s_eastus -o table 
```

## Interromper o container temporariamente
```
kubectl get deployment -n azure-store-1758905293727
kubectl scale deployment/hello-python-deployment --replicas=0 -n azure-store-1758905293727 
```
Para reiniciar:
```
kubectl scale deployment/hello-python-deployment --replicas=1 -n azure-store-1758905293727 
```

## Configurar um nome de domínio personalizado e um certificado SSL com o complemento de roteamento de aplicativo

Baseado no [Microsoft Learn](https://learn.microsoft.com/pt-br/azure/aks/app-routing-dns-ssl)


```
az provider register --namespace Microsoft.KeyVault
```

```
az keyvault create --resource-group <ResourceGroupName> --location <Location> --name <KeyVaultName> --enable-rbac-authorization true 
# az keyvault create --resource-group RG-Vaults --location eastus --name k8sgroupvault --enable-rbac-authorization true
```

```
openssl req -new -x509 -nodes -out aks-ingress-tls.crt -keyout aks-ingress-tls.key -subj "/CN=hello-python-aks.duckdns.org" -addext "subjectAltName=DNS:hello-python-aks.duckdns.org"
```


```
az keyvault certificate import --vault-name k8sgroupvault --name <KeyVaultCertificateName> --file aks-ingress-tls.pfx [--password <certificate password if specified>]
```
Em caso de erro de permissão:
```
az role assignment create  --role "Key Vault Reader"  --assignee-object-id "990a38bb-3a55-4f81-b4fe-884832be0ee3"  --scope "/subscriptions/670bc431-d5b3-4586-afcc-5b920f8c7e5e/resourcegroups/k8scluster_group/providers/Microsoft.KeyVault/vaults/k8sgroupvault"  --assignee-principal-type User
```

Agora, libere a porta 80 para expor a aplicação publicamente.
```
az network nsg rule create  --resource-group MC_k8scluster_group_clusterk8s_eastus --nsg-name aks-agentpool-30022306-nsg --name AllowHTTP --priority 100 --direction Inbound  --access Allow --protocol Tcp --destination-port-range 80 --source-address-prefixes '*' --destination-address-prefixes '*'
```


Para ver os certificados:
```
kubectl get certificates -n azure-store-1758905293727 # listar certificados
kubectl describe certificate hello-python-tls-secret -n azure-store-1758905293727 # ver mais detalhes
```

SUBNET_NAME=$(az network vnet subnet list  --resource-group MC_k8scluster_group_clusterk8s_eastus  --vnet-name aks-vnet-30022306   --query '[0].name'  -o tsv) # aks-subnet

NSG_ID=$(az network vnet subnet show --resource-group MC_k8scluster_group_clusterk8s_eastus  --vnet-name aks-vnet-30022306 --name aks-subnet --query networkSecurityGroup.id -o tsv) # /subscriptions/670bc431-d5b3-4586-afcc-5b920f8c7e5e/resourceGroups/MC_k8scluster_group_clusterk8s_eastus/providers/Microsoft.Network/networkSecurityGroups/aks-agentpool-30022306-nsg


 Exemplo: NODEPOOL_NAME="agentpool"


az aks show --resource-group k8scluster_group --name clusterk8s --query identity.principalId --output tsv

az role assignment create   --assignee c2faa1d0-4a48-4c7b-86d8-0b187ef74aa7   --role "Network Contributor"   --scope /subscriptions/$(az account show --query id -o tsv)/resourceGroups/k8scluster_group

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx   --namespace ingress-nginx   --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-resource-group"=k8scluster_group   --reuse-values