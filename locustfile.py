from locust import HttpUser, task, between

class StressTestUser(HttpUser):
    # Pausa entre 1 e 2 segundos após completar uma tarefa, simulando um usuário humano.
    # Para um teste de stress mais agressivo, você pode usar '0' ou um valor muito baixo.
    wait_time = between(1, 2) 

    @task
    def stress_cpu_endpoint(self):
        # A URL que você quer testar: a rota '/stress' com um parâmetro 'duration'
        # 'duration=0.5' fará com que o servidor consuma CPU por 0.5 segundos em CADA requisição.
        self.client.get("/stress?duration=0.5")
    
    @task
    def lista_emails(self):
        self.client.get("/lista-emails")

    @task
    def check_health(self):
        # Rota simples para verificar que o serviço está no ar
        self.client.get("/")