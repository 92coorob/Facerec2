from firebase import firebase
firebase = firebase.FirebaseApplication('https://facialrecognition-b1916.firebaseio.com', None)
result = firebase.get('/users', None)
print (result
{'1': 'John Doe', '2': 'Jane Doe'}