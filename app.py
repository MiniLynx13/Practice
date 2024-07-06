import requests
import time
import psycopg2
import logging
from flask import Flask
from flask import request

app = Flask(__name__)

def getVocations(vocation='', salary_want=None, with_salary=False, page=0):
	token = ''
	params = {
		'text': 'NAME:' + vocation,
		'salary': salary_want,
		'currency': 'RUR', #Рубли.
		'only_with_salary': with_salary,
		'area': 113, #Россия.
		'page': page,
		'per_page': 100
	}
	headers = {
        'Authorization': f'Bearer {token}'
    }
	req = requests.get('https://api.hh.ru/vacancies', params=params)
	# req = requests.get("https://api.hh.ru/vacancies", params=params, headers=headers)
	req.raise_for_status()
	req.close()
	return req.json()

def parsing(vocation='', salary_want=None, with_salary=False):
	jsObj = getVocations(vocation)
	maxpages = jsObj['pages']
	try:
		conn = psycopg2.connect(dbname='vocations', user='postgres', password='MiniLynx', host='127.0.0.2')
		logging.info('Connect to database.')
	except:
		logging.error('Can`t establish connection to database.')
		return False
	cursor = conn.cursor()
	insert_query = """
						DELETE FROM vocations
					"""
	cursor.execute(insert_query)
	for page in range(0, maxpages):
		try:
			data  = getVocations(vocation, salary_want, with_salary, page)
			if not data.get('items'):
				logging.error('Parsing error: didn`t receive items.')
				return False
			for item in data['items']:
				id = item['id']
				name = item['name']
				area = item['area'].get('name')
				salary = item['salary']
				if salary is None:
					salary_from = None
					salary_to = None
					salary_currency = None
				else:
					salary_from = item['salary'].get('from')
					salary_to = item['salary'].get('to')
					salary_currency = item['salary'].get('currency')
				apply_url = item['alternate_url']
				employer= item['employer']
				if employer is None:
					employer_name = None
				else:
					employer_name = item['employer'].get('name')
				snippet = item['snippet']
				if snippet is None:
					snippet_requirement = None
					snippet_responsibility = None
				else:
					snippet_requirement = item['snippet'].get('requirement')
					snippet_responsibility = item['snippet'].get('responsibility')
				schedule = item['schedule']
				if schedule is None:
					schedule_name = None
				else:
					schedule_name = item['schedule'].get('name')
				experience = item['experience']
				if experience is None:
					experience_name = None
				else:
					experience_name = item['experience'].get('name')
				try:
					insert_query = """
										INSERT INTO vocations 
										(id, name, area, salary_from, salary_to, salary_currency, apply_url, employer_name, snippet_requirement, snippet_responsibility, schedule_name, experience_name) 
										VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
									"""
					cursor.execute(insert_query, (id, name, area, salary_from, salary_to, salary_currency, apply_url, employer_name, snippet_requirement, snippet_responsibility, schedule_name, experience_name))
				except:
					logging.error('Error while adding data in db')
					return False
			time.sleep(0.25)
		except:
			logging.error('Error while working with db.')
			return False
	conn.commit()
	logging.info('Parsing successfully finished, data added in db.')
	return True

def filters(vocation='', salary=None, schedule='', experience='', amount=20):
	vocation = '%' + vocation + '%'
	schedule = '%' + schedule + '%'
	experience = '%' + experience + '%'
	try:
		conn = psycopg2.connect(dbname='vocations', user='postgres', password='MiniLynx', host='127.0.0.2')
		logging.info('Connect to database.')
	except:
		logging.error('Can`t establish connection to database.')
		return False, None, None
	cursor = conn.cursor()
	try:
		if salary == None:
			insert_query = """
								SELECT * FROM vocations
								WHERE name LIKE %s
									AND schedule_name LIKE %s
									AND experience_name LIKE %s
								ORDER BY id ASC
							"""
			cursor.execute(insert_query, (vocation, schedule, experience))
		else:
			insert_query = """
								SELECT * FROM vocations
								WHERE name LIKE %s
									AND schedule_name LIKE %s
									AND experience_name LIKE %s
									AND (salary_from = %s OR salary_to = %s OR (salary_from <= %s AND salary_to >= %s))
								ORDER BY id ASC
							"""
			cursor.execute(insert_query, (vocation, schedule, experience, salary, salary, salary, salary))
	except:
		logging.error('Problem with request to db.')
		return False, None, None
	try:
		data = cursor.fetchall()
		show_data = data[0:amount]
		return True, len(data), show_data
	except:
		logging.error('Problem with items.')
		return False, None, None



@app.route('/', methods=['GET', 'POST'])
def parse():
	html = """
			<!DOCTYPE html>
			<html lang="ru">

			<head>
				<meta charset="UTF-8">
				<title>Parsing</title>
			</head>

			<body>
				<h2>Парсинг вакансий с hh.ru</h2>
				<br>
				<h3>Фильтры:</h3>
				<br>
				<form method="post" action="/">
					<label for="voc">Введите должность:</label>
  					<input type="text" id="voc" name="vocation" placeholder="Аналитик">
					<br>
					<br>
					<label for="sal">Введите зарплату в рублях:</label>
  					<input type="number" id="sal" name="salary_want" placeholder="30000">
					<br>
					<br>
					<label>Только вакансии с указанной зарплатой:</label>
						<input type="radio" id="no" name="with_salary" value="False" checked>
						<label for="no">Нет</label>
   						<input type="radio" id="yes" name="with_salary" value="True">
						<label for="yes">Да</label>
					<br>
					<br>
					<br>
					<input type="submit" value="Парсить">
				</form>
				<br>
			"""
	if request.method == 'POST':
		if request.form.get('vocation'):
			vocation = request.form['vocation']
		else:
			vocation = ''
		if request.form.get('salary_want'):
			if request.form['salary_want'] > 0:
				salary_want = request.form['salary_want']
			else:
				salary_want = None
		else:
			salary_want = None
		if request.form.get('with_salary'):
			with_salary = request.form['with_salary']
		else:
			with_salary = False
		check = parsing(vocation, salary_want, with_salary)
		if check:
			html += "<p>Парсинг прошёл успешно</p>"
		else:
			html += "<p>Произошла ошибка или нет соответствующих результатов</p>"
	html += """
				<br>
				<button onclick="window.location = 'http://127.0.0.1:5000/filters';">Перейти к просмотру вакансий</button>
			</body>

			</html>
			"""
	return html
	



@app.route('/filters', methods=['GET', 'POST'])
def analysis():
	html = """
			<!DOCTYPE html>
			<html lang="ru">

			<head>
				<meta charset="UTF-8">
				<title>Filters</title>
			</head>

			<body>
				<h2>Поиск вакансий</h2>
				<br>
				<button onclick="window.location = 'http://127.0.0.1:5000/';">Вернуться к парсингу вакансий</button>
				<br>
				<br>
				<h3>Фильтры:</h3>
				<br>
				<form method="post" action="/filters">
					<label for="voc">Введите должность:</label>
  					<input type="text" id="voc" name="vocation" placeholder="Аналитик">
					<br>
					<br>
					<label for="sal">Введите зарплату в рублях:</label>
  					<input type="number" id="sal" name="salary" placeholder="30000">
					<br>
					<br>
					<label>Режим работы:</label><br>
						<input type="radio" id="no_schedule" name="schedule" value="" checked>
						<label for="no_schedule">Не указан</label><br>
						<input type="radio" id="fullDay" name="schedule" value="Полный день">
						<label for="fullDay">Полный день</label><br>
   						<input type="radio" id="shift" name="schedule" value="Сменный график">
						<label for="shift">Сменный график</label><br>
						<input type="radio" id="flexible" name="schedule" value="Гибкий график">
						<label for="flexible">Гибкий график</label><br>
   						<input type="radio" id="remote" name="schedule" value="Удаленная работа">
						<label for="remote">Удаленная работа</label><br>
						<input type="radio" id="flyInFlyOut" name="schedule" value="Вахтовый метод">
						<label for="flyInFlyOut">Вахтовый метод</label><br>
					<br>
					<label>Необходимый стаж:</label><br>
						<input type="radio" id="no_experience" name="experience" value="" checked>
						<label for="no_experience">Не указан</label><br>
						<input type="radio" id="noExperience" name="experience" value="Нет опыта">
						<label for="noExperience">Нет опыта</label><br>
						<input type="radio" id="between1And3" name="experience" value="От 1 года до 3 лет">
						<label for="between1And3">От 1 года до 3 лет</label><br>
						<input type="radio" id="between3And6" name="experience" value="От 3 до 6 лет">
						<label for="between3And6">От 3 до 6 лет</label><br>
						<input type="radio" id="moreThan6" name="experience" value="Более 6 лет">
						<label for="moreThan6">Более 6 лет</label><br>
					<br>
					<label for="amount">Введите количество отображаемых вакансий:</label>
  					<input type="number" id="amount" name="amount" placeholder="20">
					<br>
					<br>
					<br>
					<input type="submit" value="Найти вакансии">
				</form>
				<br>
				<br>
			"""
	if request.method == 'POST':
		if request.form.get('vocation'):
			vocation = request.form['vocation']
		else:
			vocation = ''
		if request.form.get('salary'):
			if request.form['salary'] > 0:
				salary = request.form['salary']
			else:
				salary = None
		else:
			salary = None
		if request.form.get('schedule'):
			schedule = request.form['schedule']
		else:
			schedule = ''
		if request.form.get('experience'):
			experience = request.form['experience']
		else:
			experience = ''
		if request.form.get('amount'):
			if request.form['amount'] > 0:
				amount = request.form['amount']
			else:
				amount = 1
		else:
			amount = 20
		check, len_data, data = filters(vocation, salary, schedule, experience, amount)
		if check:
			html += f"""
						<h3>Количество вакансий: {len_data}</h3>
						<br>
					"""
			if len_data > 0:
				if amount <= len_data:
					html += f"""
								<h3>Первые {amount} вакансий:</h3>
								<br>
							"""
				else:
					html += f"""
								<h3>Первые {len_data} вакансий:</h3>
								<br>
							"""
				for item in data:
					html += f"""
							<h7>Должность: {item[1]}</h7><br>
							<h7>Город: {item[2]}</h7><br>
							<h7>Работодатель: {item[7]}</h7><br>
						"""
					if item[5] == None:
						html += f"<h7>Зарплата: Не указана</h7><br>"
					elif item[3] == None:
						html += f"<h7>Зарплата: до {item[4]} {item[5]}</h7><br>"
					elif item[4] == None:
						html += f"<h7>Зарплата: от {item[3]} {item[5]}</h7><br>"
					else:
						html += f"<h7>Зарплата: от {item[3]} до {item[4]} {item[5]}</h7><br>"
					html += f"""
							<h7>Режим работы: {item[10]}</h7><br>
							<h7>Стаж: {item[11]}</h7><br>
							<h7>Ссылка: {item[6]}</h7>
							<hr>
						"""
		else:
			html += "<p>Произошла ошибка или нет соответствующих результатов</p>"
	html += """
			</body>

			</html>
			"""
	return html

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)
	app.run(host='127.0.0.1', port='5000')
